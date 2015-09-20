#Standard Library Imports
import sys, time, datetime, logging, MySQLdb
import argparse
from threading import Thread
from Queue import Queue

#Third Party Imports
from EagleClass import to_epoch_2000

#Local Application/Library Specific Imports
import config
import HydroMeter

class UpdateDB(Thread):

    def __init__(self, cfg, queueResults ):
        Thread.__init__(self)
        self.queueResults = queueResults

        self.logger = cfg.setLogging(self.__class__.__name__)
        self.cfg = cfg

        cfg.setdefault("SQL.host", default = "localhost")
        cfg.setdefault("SQL.user", default = "user")
        cfg.setdefault("SQL.passwd", default = "???")
        cfg.setdefault("SQL.db", default = "db")

    def run(self, exit_on_empty_queue = False) :
        db = None
        loop_forever = True

        while loop_forever:
            data = self.queueResults.get()
            self.queueResults.task_done()

            try:
                # Connect to the database
                db = MySQLdb.connect(self.cfg["SQL.host"],self.cfg["SQL.user"],self.cfg["SQL.passwd"],self.cfg["SQL.db"])

                # Setup a cursor object using cursor() method
                cursor = db.cursor()

                while data != None:
                  try:
                    # perform SQL action
                    #cursor.execute("""INSERT INTO `BCHYDRO_DATA` (`CIRCUIT`,`DATE_TIME`,`POWER_KWH`) VALUES (%s,%s,%s)""",
                    cursor.execute("""INSERT INTO `BCHYDRO_DATA` (`CIRCUIT`,`DATE_TIME`,`POWER_KWH`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE POWER_KWH=VALUES(POWER_KWH)""",
                           (data[0],data[1],data[2]))

                    db.commit()
                    self.logger.info("Updated: " + data[0] + " = " + str(data[2]) + " at " + data[1])
                  except Exception, e_n:
                    self.logger.warning ("Update failed: " + data[0] + " = " + str(data[2]) + " at " + data[1])
                    self.logger.warning(str(e_n))

                  # Get more data if immediately available so that
                  # we take advantage of the open database connection
                  if (self.queueResults.empty() ):
                        data = None
                        if (exit_on_empty_queue):
                            loop_forever = False
                  else:
                        data = self.queueResults.get()
                        time.sleep(.05) # make sure we do not hog the CPU
                        self.queueResults.task_done()

            except Exception, e:
                # failed to add row to DB ... wait 10 min and try again
                self.logger.warning(str(e))
                self.queueResults.put(data)
                time.sleep(10*60)

            finally:
                # close the mysql database connection
                if (db != None):
			db.close()
                        db = None

if __name__ == "__main__":
    # Setup basic logging ability until config data is parsed
    logging.basicConfig(format='%(levelname) -10s (%(threadName)-10s) %(asctime)s %(module)s:%(funcName)s[%(lineno)s] %(message)s',
                                                    level="INFO")

    # create custom argument parsing
    parser = argparse.ArgumentParser(description="Upload BC Hydro meter readings to SQL DB")

    parser.add_argument("-s", "--startdate", dest="start_date",
                    default="2015-01-01",
                    help="Starting date for history (%Y-%m-%d)")

    parser.add_argument("-e", "--enddate", dest="end_date",
                    default=None,
                    help="Ending date for history (%Y-%m-%d)")

    # read YML config data
    cfg = config.config(parser=parser)
    cfg.setLogging()

    print "start: " + cfg.results.start_date
    if cfg.results.end_date != None:
        print "end: " + cfg.results.end_date
        
    queueDB        = Queue()

    # setup database thread
    updateDB = UpdateDB(cfg, queueResults = queueDB)

    meter = HydroMeter.Meter(cfg, queue_db = queueDB)
    meter.summarize_history_data_by_hour(cfg.results.start_date, cfg.results.end_date)

    try:
      updateDB.run(exit_on_empty_queue = True)
    except KeyboardInterrupt :
      print "Interrupt"
      exit(0)

