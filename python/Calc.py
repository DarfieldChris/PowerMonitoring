#Standard Library Imports
import sys, serial, time, datetime, logging, csv
from threading import Thread
from Queue import Queue

#Third Party Imports

#Local Application/Library Specific Imports
import config

class Calc(Thread):

    def dataOpen(self):
        self.f = open(self.fileCSV, 'wt')

        fieldnames = ("DATE_TIME", "Irms")
        self.writer = csv.DictWriter(self.f, fieldnames=fieldnames)
        headers = dict( (n,n) for n in fieldnames )
        self.writer.writerow(headers)


    def __init__(self, cfg, queueReadings, queueResults, broadcast_queue = None, fileCSV='data.csv'):
        Thread.__init__(self)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.cfg = cfg
        self.broadcast_queue = broadcast_queue
        self.queueReadings = queueReadings
        self.queueResults = queueResults
        self.fileCSV = fileCSV
        self.timeNextDay = time.time() + 24*60*60

        self.readings = {}

        self.dataOpen()

    def run(self) :
        while True :
            data = self.queueReadings.get()
            _id = data[0]

            # valid data - what do I do?
            #_time = (int)(data[1])/1000 
            _time = data[1]
            _ts = time.time()

            if ( self.cfg.setdefault("Circuits." + _id + ".type", default="???") == "kw" ) :
                # accumulate kw-hrs
                timeLastReading = self.readings.get(_id + "tlr", 0.0) 
                if ( timeLastReading > 0 ):
                    self.readings[_id + "kwhrs"] = self.readings.get(_id + "kwhrs", 0.0) + self.readings.get(_id + "alr",0.0001)*(_time - timeLastReading)
                    _timeNextHour = self.readings[_id + "tnh"]
                    if ( _ts > _timeNextHour):
                        # we have accumulated an hour of readings
                        # what should I do with it?
                        t = datetime.datetime.fromtimestamp(_timeNextHour - 3600 + 1).strftime('%Y-%m-%d %H:%M:%S')
                        kwhrs = self.readings[_id + "kwhrs"]/3600
                        self.queueResults.put([_id,t,kwhrs])

                        # reset for the next hour of readings
                        self.readings[_id + "tnh"] = _timeNextHour + 60*60
                        self.readings[_id + "kwhrs"] = 0.0
                else:
                    self.readings[_id + "tnh"] = ( _ts // (60*60))*3600 + 60*60
            else:
                self.logger.debug("No type for circuit %s (%s)", _id, self.cfg['Circuits'].keys() )


            # broadcast the most recent data if desired
            if (self.broadcast_queue != None):
                # Only broadcast if the reading has changed
                #self.logger.info("FLOAT ?: %s", data[2])
                if (self.readings.get(_id + "alr", 0.0001) != (float)(data[2])):
                    self.broadcast_queue.put ([_id, _ts, data[2]])
                
            self.readings[_id + "tlr"] = _time
            self.readings[_id + "alr"] = (float)(data[2])

            # log the raw current readings in a data file
            if ( _ts > self.timeNextDay):
                self.f.close()
                self.timeNextDay += 24*60*60
                self.dataOpen()

            t = datetime.datetime.fromtimestamp(_ts).strftime('%Y-%m-%d %H:%M:%S')
            self.logger.debug("Date: %s Irms(%s): %s", t, _id, data[2])

            self.writer.writerow({ 'DATE_TIME':t,'Irms':data[2]})

            self.queueReadings.task_done()
