#! /usr/bin/env python

#Standard Library Imports
import sys, time, datetime, logging
from threading import Thread
from Queue import Queue

#Third Party Imports
from apscheduler.schedulers.background import BackgroundScheduler

#Local Application/Library Specific Imports
import config

class ArdSchedule(Thread):

  def __init__(self,cfg,queueToArduino):
      Thread.__init__(self)

      self.queueToArduino = queueToArduino
      self.cfg = cfg

      self.scheduler = BackgroundScheduler()


  def run(self):
      self.scheduler.start()
      while True:
           time.sleep(60)

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

