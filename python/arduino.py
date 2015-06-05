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

#Standard Library Imports
import sys, serial, select, time, datetime, logging, glob, socket, struct, csv, MySQLdb
from threading import Thread
from Queue import Queue
from socket import AF_INET, SOCK_DGRAM

#Third Party Imports

#Local Application/Library Specific Imports
import config
import mqtt

class UpdateDB(Thread):

    def __init__(self, cfg, queueResults ):
        Thread.__init__(self)
        self.queueResults = queueResults

        self.cfg = cfg

        cfg.setdefault("SQL.host", default = "localhost")
        cfg.setdefault("SQL.user", default = "user")
        cfg.setdefault("SQL.passwd", default = "???")
        cfg.setdefault("SQL.db", default = "db")

    def run(self) :
        while True :
            data = self.queueResults.get()

            try:
                # Connect to the database
                db = MySQLdb.connect(self.cfg["SQL.host"],self.cfg["SQL.user"],self.cfg["SQL.passwd"],self.cfg["SQL.db"])

                # Setup a cursor object using cursor() method
                cursor = db.cursor()

                # perform SQL action
                cursor.execute("""INSERT INTO `BCHYDRO_DATA` (`CIRCUIT`,`DATE_TIME`,`POWER_KWH`) VALUES (%s,%s,%s)""", 
                           (data[0],data[1],data[2],))

                db.commit()

                # close the mysql database connection
                db.close()

                logging.info ("Updated database.")

            except MySQLdb.Error, e:
                # failed to add row to DB ... wait 10 min and try again
                logging.warning(str(e))
                self.queueResults.put(data)
                time.sleep(10*60)

            self.queueResults.task_done()

class Calc(Thread):
    broadcast_queue = None

    def dataOpen(self):
        self.f = open(self.fileCSV, 'wt')

        fieldnames = ("DATE_TIME", "Irms")
        self.writer = csv.DictWriter(self.f, fieldnames=fieldnames)
        headers = dict( (n,n) for n in fieldnames )
        self.writer.writerow(headers)


    def __init__(self, queueReadings, queueResults, fileCSV='data.csv'):
        Thread.__init__(self)

        self.queueReadings = queueReadings
        self.queueResults = queueResults
        #self.timeRef = timeRef
        self.fileCSV = fileCSV
        #self.timeNextDay = self.timeRef + 24*60*60
        self.timeNextDay = time.time() + 24*60*60
        #self.timeNextHour = (self.timeRef // (60*60))*3600 + 60*60

        self.readings = {}
        #self.timeLastReading = 0
        #self.ampsLastReading = 0
        #self.kwhrs = 0

        self.dataOpen()

    def run(self) :
        while True :
            str = self.queueReadings.get()
            data = str.split(":")

            if ( (len(data) != 3 and len(data) != 6) or str[0] != '!' ):
                logging.warning("invalid data: %s", str)
            else:
                _id = data[0][1:]
                logging.debug("valid data: %s", _id)

                # valid data - what do I do?
                #_time = (int)(data[1])/1000 + self.timeRef
                _time = (int)(data[1])/1000 
                _ts = time.time()

                # accumulate kw-hrs
                timeLastReading = self.readings.get(_id + "tlr", 0) 
                if ( timeLastReading > 0 ):
                    #self.kwhrs += self.ampsLastReading*(_time - timeLastReading)
                    self.readings[_id + "kwhrs"] = self.readings.get(_id + "kwhrs", 0.0) + self.readings.get(_id + "alr",0.0001)*(_time - timeLastReading)
                    #if (_time > self.timeNextHour):
                    _timeNextHour = self.readings[_id + "tnh"]
                    #if (_time > _timeNextHour):
                    if ( _ts > _timeNextHour):
                        # we have accumulated an hour of readings
                        # what should I do with it?
                        t = datetime.datetime.fromtimestamp(_timeNextHour - 3600 + 1).strftime('%Y-%m-%d %H:%M:%S')
                        #self.kwhrs = self.kwhrs*240/3600*.001
                        kwhrs = self.readings[_id + "kwhrs"]*240/3600*.001
                        self.queueResults.put([_id,t,kwhrs])

                        # reset for the next hour of readings
                        self.readings[_id + "tnh"] = _timeNextHour + 60*60
                        self.readings[_id + "kwhrs"] = 0.0
                else:
                    self.readings[_id + "tnh"] = ( _ts // (60*60))*3600 + 60*60

                # broadcast the most recent data if desired
                if (self.broadcast_queue != None):
                    # Only broadcast if the reading has changed
                    if (self.readings.get(_id + "alr", 0.0001) != (float)(data[2])):
                        #self.broadcast_queue.put ([_id, _time, data[2]])
                        self.broadcast_queue.put ([_id, _ts, data[2]])
                
                #self.timeLastReading = _time
                self.readings[_id + "tlr"] = _time
                #self.ampsLastReading = (float)(data[2])
                self.readings[_id + "alr"] = (float)(data[2])

                # log the raw current readings in a data file
                if ( _ts > self.timeNextDay):
                    self.f.close()
                    self.timeNextDay += 24*60*60
                    self.dataOpen()

                t = datetime.datetime.fromtimestamp(_ts).strftime('%Y-%m-%d %H:%M:%S')
                logging.debug("Date: %s Irms(%s): %s", t, _id, data[2])

                self.writer.writerow({ 'DATE_TIME':t,'Irms':data[2]})

            self.queueReadings.task_done()

class Arduino(Thread) :
    def __init__(self, cfg, 
                 ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*"),
                 queueFromArduino = None, queueToArduino=None):
        Thread.__init__(self)
        cfg.setdefault("Arduino.baud", default = 9600)
        self.ports = ports
        self.ser = None
        self.queueFrom = queueFromArduino
        self.queueTo = queueToArduino
        self.cfg = cfg

    def _connect(self) :
        logging.debug("Starting using " + str(self.cfg["Arduino.baud"]) + " baud ...")
        # Port may vary, so look for the right one:
        if not len(self.ports) :
            self.ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")

        for port in self.ports :
            logging.debug("Trying port " + port)
            if self.ser : 
                logging.debug("The port is already set.")
                break
            try :
                logging.debug("Attempting to connect to " + port + " at " + str(self.cfg["Arduino.baud"]))
                self.ser = serial.Serial(port, self.cfg["Arduino.baud"], timeout=1)
                logging.info("Opened port %s" % port)
                break
            except :
                logging.warn("Failed to open port %s" % port)
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

            # Check for data in the inbound queue
            if (self.queueTo and self.queueTo.qsize() > 0):
                data = self.queueTo.get()
                logging.debug("Sending to arduino: " + data[0] + ":" + data[1])
                #self.ser.write(data[0]+':'+data[1]+'\n')
                self.ser.write(data[0])
                

            # check for Arduino output:
            if self.ser in inp :
                line = self.ser.readline().strip()
                logging.debug( "Arduino: %s" % line)
                if (self.queueFrom ):
                    self.queueFrom.put(line)

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

    # read YML config data
    cfg = config.config()
    
    # Setup logging
    #logging.basicConfig(level=logging.DEBUG,
    #                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
    #                    )
    cfg.setLogging()

    #logging.info("Current time is %s" % time.ctime(getNTPTime()).replace("  "," "))

    # create queues to pass data between the different threads
    queueArduino = Queue()
    queueDB = Queue()
    queueMqttPub = Queue()

    # Setup Mqtt client thread
    mqtt_client = mqtt.mqtt(cfg)
    mqtt_client.publish_queue = queueMqttPub
    mqtt_client.daemon = True
    mqtt_client.start()

    # setup Arduino thread

    ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")
    logging.info("Will connect to Arduino using ports: %s" % ports)

    arduino = Arduino(cfg, ports=ports, queue=queueArduino)
 
    # setup calculation thread
    threadCalc = Calc(queueReadings=queueArduino, queueResults=queueDB)
    #threadCalc = Calc(queueReadings=queueArduino, queueResults=queueDB, timeRef = getNTPTime())
    threadCalc.broadcast_queue = queueMqttPub
    threadCalc.daemon = True
    threadCalc.start()

    # setup database thread
    updateDB = UpdateDB(cfg, queueResults = queueDB)
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

