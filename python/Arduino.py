#! /usr/bin/env python

#Standard Library Imports
import sys, serial, select, time, datetime, logging, glob
from threading import Thread
from Queue import Queue

#Third Party Imports
from apscheduler.schedulers.background import BackgroundScheduler

#Local Application/Library Specific Imports
import config

def state_change(name, state, _queue):
    _queue.put([name, state])
    logging.info(name + " - " + state)
        
class ArdSchedule(Thread):

  def __init__(self,cfg,queueToArduino):
      Thread.__init__(self)

      self.logger = cfg.setLogging(self.__class__.__name__)

      self.queueToArduino = queueToArduino
      self.cfg = cfg

      self.scheduler = BackgroundScheduler()

  def initialize(self):
    # set initial conditions of Arduino outputs
    nr = datetime.datetime.now() + datetime.timedelta(seconds=15)
    #self.logger.info("kk: " + nr)
    if (datetime.datetime.now().hour > 6 and datetime.datetime.now().hour < 17 ) :
        self.scheduler.add_job(state_change, 'date', run_date=nr, args=['HWTrelay', '0',self.queueToArduino])
    else:
        self.scheduler.add_job(state_change, 'date', run_date=nr, args=['HWTrelay', '1',self.queueToArduino])

    self.scheduler.add_job(state_change, 'cron', hour='6', minute='30', args=['HWTrelay', '0',self.queueToArduino])
    self.scheduler.add_job(state_change, 'cron', hour='17', minute='30', args=['HWTrelay', '1',self.queueToArduino])                                     
  def run(self):
      self.scheduler.start()
      while True:
           time.sleep(60)

class Arduino(Thread) :
    def __init__(self, cfg, 
                 ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*"),
                 queueFromArduino = None, queueToArduino=None):

        Thread.__init__(self)

        self.logger = cfg.setLogging(self.__class__.__name__)

        cfg.setdefault("Arduino.baud", default = 9600)
        self.ports = ports
        self.ser = None
        self.queueFrom = queueFromArduino
        self.queueTo = queueToArduino
        self.cfg = cfg

    def _connect(self) :
        self.logger.debug("Starting using " + str(self.cfg["Arduino.baud"]) + " baud ...")
        # Port may vary, so look for the right one:
        if not len(self.ports) :
            self.ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")

        for port in self.ports :
            self.logger.info("Trying port " + port + " to connect to Arduino.")
            if self.ser : 
                self.logger.debug("The port is already set.")
                break
            try :
                self.logger.debug("Attempting to connect to " + port + " at " + str(self.cfg["Arduino.baud"]))
                self.ser = serial.Serial(port, self.cfg["Arduino.baud"], timeout=1)
                self.logger.info("Opened port %s" % port)
                break
            except :
                self.logger.warning("Failed to open port %s" % port)
                self.ser = None
                pass
        return self.ser


    def run(self) :
        while True :
          while (not self.ser):
              self.logger.info("Attempting to open serial port to Arduino ...")
              if (self._connect() == None ) :
                 self.logger.warning("Failed to open serial port to Arduino.  Will retry in 5 seconds ...")
                 time.sleep(5)

          #flush the serial connection to the Arduino before we start
          self.ser.write('\n')
          self.ser.flushInput()

          try:
            # Check whether the user has typed anything:
            inp, outp, err = select.select([sys.stdin, self.ser], [], [], .2)

            # Check for user input:
            if sys.stdin in inp :
                line = sys.stdin.readline()
                if (line[0] == '!' ):
                    try:
                        #exec line[1:]
                        a = eval (line[1:])
                        self.logger.info ("Evaluated input: " + str(a))
                    except:
                        self.logger.info("Failed to evaluate: " + line)
                else:
                    self.ser.write(line)
                    self.logger.info ("Input to arduino: " + line)

            # Check for data in the inbound queue
            if (self.queueTo and self.queueTo.qsize() > 0):
                data = self.queueTo.get()
                self.logger.info("Sending to arduino: " + data[0] + ":" + data[1])
                self.ser.write(data[0]+':'+data[1]+'\n')
                #self.ser.write(data[0])
                self.queueTo.task_done()
                
            # check for Arduino output:
            if self.ser in inp :
                line = self.ser.readline()
                self.logger.debug( "Arduino: %s" % line)
                line = line.strip()

                data = line.split(":")

                if ( (len(data) != 3 and len(data) != 6) or line[0] != '!' ):
                    self.logger.warning("invalid data: %s", line)
                else:
                    data[0] = data[0][1:]
                    # the arduino timestamp is in milliseconds ... convert to seconds
                    data[1] = (int)(data[1])/1000.0 
                    self.logger.debug("valid data: %s %s", data[0], data[2])
                    if (self.queueFrom ):
                        self.queueFrom.put(data)

          except serial.SerialException :
            self.ser = None
            self.logger.warning("Lost serial connection to Arduino.  Will retry ...")


if __name__ == "__main__":

    def tick():
        print('Tick! The time is: %s' % datetime.datetime.now())
                      
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

    ards = ArdSchedule(cfg,queueArduino)
    ards.scheduler.add_job(tick, 'interval', seconds=5)
    ards.run()

