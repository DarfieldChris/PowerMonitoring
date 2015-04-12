#! /usr/bin/env python

# arduino.py
#
# Monitor residential power consumption
#
# This program consists of 3 seperate threads:
#      1 - UpdateDB
#      2 - Calc
#      3 - Arduino
#
# Arduino - This is the main thread of the program; it monitors a USB connected arduino 
#           and dumps current measurements into a calculations queue
# Calc    - This thread processes current measurements into power consumption data and 
#           every hour dumps the results into an update queue
# UpdateDB- This thread writes hourly consumption data in kw-hrs to an SQL database
#
# See the project README.md for Copyright.

import sys, serial, select, time, datetime, logging, glob, socket, struct, csv, MySQLdb
from threading import Thread
from Queue import Queue
from socket import AF_INET, SOCK_DGRAM

class UpdateDB(Thread):
    def __init__(self, queueResults, SQL_HOST = "localhost", SQL_USER = "user", SQL_PASSWD = "???", SQL_DB = "db"):
        Thread.__init__(self)
        self.queueResults = queueResults

        self.SQL_HOST = SQL_HOST
        self.SQL_USER = SQL_USER
        self.SQL_PASSWD = SQL_PASSWD
        self.SQL_DB = SQL_DB

    def run(self) :
        while True :
            data = self.queueResults.get()

            # Connect to the database
            db = MySQLdb.connect(self.SQL_HOST,self.SQL_USER,self.SQL_PASSWD,self.SQL_DB)

            # Setup a cursor object using cursor() method
            cursor = db.cursor()

            # perform SQL action
            cursor.execute("""INSERT INTO `BCHYDRO_DATA` (`CIRCUIT`,`DATE_TIME`,`POWER_KWH`) VALUES (%s,%s,%s)""", 
                           (data[0],data[1],data[2],))

            db.commit()

            # close the mysql database connection
            db.close()

            self.queueResults.task_done()

class Calc(Thread):
    def dataOpen(self):
        self.f = open(self.fileCSV, 'wt')

        fieldnames = ("DATE_TIME", "Irms")
        self.writer = csv.DictWriter(self.f, fieldnames=fieldnames)
        headers = dict( (n,n) for n in fieldnames )
        self.writer.writerow(headers)


    def __init__(self, queueReadings, queueResults, timeRef, fileCSV='data.csv'):
        Thread.__init__(self)

        self.queueReadings = queueReadings
        self.queueResults = queueResults
        self.timeRef = timeRef
        self.fileCSV = fileCSV
        self.timeNextDay = self.timeRef + 24*60*60
        self.timeNextHour = (self.timeRef // (60*60))*3600 + 60*60

        self.timeLastReading = 0
        self.ampsLastReading = 0
        self.kwhrs = 0

        self.dataOpen()


    def run(self) :
        while True :
            str = self.queueReadings.get()
            data = str.split(":");

            if ( len(data) == 6 ):
                #logging.debug("valid data")

                # valid data - what do I do?
                _time = (int)(data[1])/1000 + self.timeRef

                # accumulate kw-hrs
                if ( self.timeLastReading > 0 ):
                    self.kwhrs += self.ampsLastReading*(_time - self.timeLastReading)
                    if (_time > self.timeNextHour):
                        # we have accumulated an hour of readings
                        # what should I do with it?
                        t = datetime.datetime.fromtimestamp(self.timeNextHour - 3600 + 1).strftime('%Y-%m-%d %H:%M:%S')
                        self.kwhrs = self.kwhrs*240/3600*.001
                        self.queueResults.put([data[0],t,self.kwhrs])

                        # reset for the next hour of readings
                        self.timeNextHour += 60*60
                        self.kwhrs = 0
                self.timeLastReading = _time
                self.ampsLastReading = (float)(data[5])

                # log the raw current readings in a data file
                if (_time > self.timeNextDay):
                    self.f.close()
                    self.timeNextDay += 24*60*60
                    dataOpen(self)

                t = datetime.datetime.fromtimestamp(_time).strftime('%Y-%m-%d %H:%M:%S')
                logging.info("Date: %s Irms: %s", t, self.ampsLastReading)

                self.writer.writerow({ 'DATE_TIME':t,'Irms':data[5]})

            self.queueReadings.task_done()

class Arduino(Thread) :
    def __init__(self, baud=9600, 
                 ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*"),
                 queue = None):
        Thread.__init__(self)
        self.baud=baud
        self.ports=ports
        self.ser = None
        self.queue = queue

    def _connect(self) :
        # Port may vary, so look for the right one:
        if not len(self.ports) :
            self.ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")

        for port in self.ports :
            if self.ser : 
                break
            try :
                    self.ser = serial.Serial(port, self.baud, timeout=1)
                    logging.info("Opened port %s" % port)
                    break
            except :
                    self.ser = None
                    pass
        return self.ser


    def run(self) :
        while True :
          while (not self.ser):
              logging.info("Attempting to open serial port to Arduino ...")
              if (self._connect() == None ) :
                 logging.warning("Failed to open serial port to Arduino.  Will retry in 5 seconds ...")
                 time.sleep(5)

          self.ser.flushInput()

          try:
            # Check whether the user has typed anything:
            inp, outp, err = select.select([sys.stdin, self.ser], [], [], .2)

            # Check for user input:
            if sys.stdin in inp :
                line = sys.stdin.readline()
                self.ser.write(line)

            # check for Arduino output:
            if self.ser in inp :
                line = self.ser.readline().strip()
                logging.debug( "Arduino: %s" % line)
                self.queue.put(line)

          except serial.SerialException :
            self.ser = None
            logging.warning("Lost serial connection to Arduino.  Will retry ...")


if __name__ == "__main__":

    # Procedure to query network time server for current time stamp
    def getNTPTime(host = "pool.ntp.org"):
        port = 123
        buf = 1024
        address = (host,port)
        msg = '\x1b' + 47 * '\0'

        # reference time (in seconds since 1900-01-01 00:00:00)
        TIME1970 = 2208988800L # 1970-01-01 00:00:00

        # connect to server
        client = socket.socket( AF_INET, SOCK_DGRAM)
        client.sendto(msg, address)
        msg, address = client.recvfrom( buf )

        t = struct.unpack( "!12I", msg )[10]
        t -= TIME1970
        return t

    # Setup logging
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                        )

    #logging.info("Current time is %s" % time.ctime(getNTPTime()).replace("  "," "))

    # create queues to pass data between the different threads
    queueArduino = Queue()
    queueDB = Queue()

    # setup Arduino thread
    baud = 9600
    if (len(sys.argv) > 1) :
        baud = int(sys.argv[1])
    logging.info("Will connect to arduino at %d baud" % baud)

    ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")
    if (len(sys.argv) > 2 ) :
        ports = argv[2]
    logging.info("Will connect to Arduino using ports: %s" % ports)

    arduino = Arduino(baud=baud, ports=ports, queue=queueArduino)
 
    # setup calculation thread
    threadCalc = Calc(queueReadings=queueArduino, queueResults=queueDB, timeRef = getNTPTime())
    threadCalc.daemon = True
    threadCalc.start()

    # setup database thread
    updateDB = UpdateDB(queueResults = queueDB, 
                        SQL_HOST = "xxx",
                        SQL_USER = "xxx",
                        SQL_PASSWD = "xxx",
                        SQL_DB = "xxx")
    updateDB.daemon = True
    updateDB.start()

    # start main thread of execution
    try :
      arduino.run()
    except serial.SerialException :
      logging.error("Disconnected (Serial exception)")
    except IOError :
      logging.error("Disconnected (I/O Error)")
    except KeyboardInterrupt :
      print "Interrupt"
      exit(0)

