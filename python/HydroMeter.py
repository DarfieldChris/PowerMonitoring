#! /usr/bin/env python

#Standard Library Imports
import sys, os, serial, time, datetime, logging
import argparse
from threading import Thread
from Queue import Queue

#Third Party Imports
from EagleClass import Eagle, to_epoch_1970, to_epoch_2000

#Local Application/Library Specific Imports
import config

def twos_comp(val, bits=32):
    """compute the 2's compliment of int value val"""
    if( (val&(1<<(bits-1))) != 0 ):
        val = val - (1<<bits)
    return val


def print_currentsummation(cs) :

    multiplier = int(cs['Multiplier'], 16)
    divisor = int(cs['Divisor'], 16)
    delivered = int(cs['SummationDelivered'], 16)
    received = int(cs['SummationReceived'], 16)

    if multiplier == 0 :
        multiplier = 1

    if divisor == 0 :
        divisor = 1

    reading_received = received * multiplier / float (divisor)
    reading_delivered = delivered * multiplier / float (divisor)

    if 'TimeStamp' in cs :
        time_stamp = to_epoch_1970(cs['TimeStamp'])
        print "{0:s} : ".format(time.asctime(time.localtime(time_stamp)))
    print "\tReceived  = {0:{width}.3f} Kw".format(reading_received, width=10)
    print "\tDelivered = {0:{width}.3f} Kw".format(reading_delivered, width=10)
    print "\t\t{0:{width}.3f} Kw".format( (reading_delivered - reading_received), width=14)


def calc_kws(idemand) :
    multiplier = int(idemand['Multiplier'], 16)
    divisor = int(idemand['Divisor'], 16)

#    demand = twos_comp(int(idemand['Demand'], 16))

    demand = int(idemand['Demand'], 16)

    if demand > 0x7FFFFFFF:
        demand -= 0x100000000

    if multiplier == 0 :
        multiplier = 1

    if divisor == 0 :
        divisor = 1

    idemand['kws'] = (demand * multiplier) / float (divisor)

    return idemand['kws']

def print_instantdemand(idemand) :
    
    if 'TimeStamp' in idemand :
        time_stamp = to_epoch_1970(idemand['TimeStamp'])
        print "{0:s} : ".format(time.asctime(time.localtime(time_stamp)))

    print "\tDemand    = {0:{width}.3f} Kw".format(idemand['kws'], width=10)
    print "\tAmps      = {0:{width}.3f}".format( ((idemand['kws'] * 1000) / 240), width=10)
    #print ("\t", idemand)

class Meter(Thread) :
    def getEagle(self):
        if ( self.eg == None) :
            try:
                self.eg = Eagle(addr = self.cfg["Eagle.addr"], port = self.cfg["Eagle.port"],
                        debug = self.cfg["Eagle.debug"], timeout = self.cfg["Eagle.timeout"])
            except Exception, e:
                self.logger.warning("Failed to connect to the meter")
                self.logger.warning(str(e_n))
                raise e

        return self.eg

    def __init__(self,cfg,queue_readings = None, queue_db = None):
        Thread.__init__(self)

        self.logger = cfg.setLogging(self.__class__.__name__)
        self.cfg = cfg

        self.queue_readings = queue_readings
        self.queue_db = queue_db

        self.kws = -1.0

        self.timeOfLastReading = 0.0
        self.timeOfFailure = time.time()
        self.timeOfReconnection = -1.0

        self.eg = None
        self.getEagle()

    def parse_time(self, _time = None):
        res = None

        if ( _time != None ):
            if ( type(_time) == type('') ):
                self.logger.debug( "Got string" )
                struct_time = time.strptime(_time, "%Y-%m-%d")
                res = to_epoch_2000(struct_time)
            else:
                self.logger.debug("Not a string %s" % type(_time))
                res = to_epoch_2000(_time)

        return res

    def summarize_history_data_by_hour(self, date_start=0, date_end = None, to_stdout = True):
        if ( self.getEagle() == None ):
            self.logger.info( "Cannot get history data ... not connected" )
            return

        st = self.parse_time(date_start)
        et = self.parse_time(date_end)
        rh = self.getEagle().get_history_data(starttime=st, endtime=et)

        last_delivered = -1.0
        last_received  = -1.0
        time_now = 0
        time_prev = 0
        hour_delta_received = 0.0
        hour_delta_delivered= 0.0

        x = 0
        print rh
        total = len(rh['HistoryData']['CurrentSummation'])
        for cs in rh['HistoryData']['CurrentSummation'] :
            x = x + 1

            time_now = to_epoch_1970(cs['TimeStamp'])

            multiplier = int(cs['Multiplier'], 16)
            divisor = int(cs['Divisor'], 16)
            delivered = int(cs['SummationDelivered'], 16)
            received = int(cs['SummationReceived'], 16)

            # print "Multiplier=", multiplier, "Divisor=", divisor, "Demand=", demand

            if multiplier == 0 :
               multiplier = 1

            if divisor == 0 :
                divisor = 1

            reading_received = received * multiplier / float(divisor)
            if (last_received > 0):
                delta_received = (reading_received - last_received)
            else:
                delta_received = 0
            last_received = reading_received

            reading_delivered = delivered * multiplier / float(divisor)
            if (last_delivered > 0):
                delta_delivered = (reading_delivered - last_delivered)
            else:
                delta_delivered = 0
            last_delivered = reading_delivered

            ts_now = time.localtime(time_now)

            if time_prev > 0 :
              ts_prev = time.localtime(time_prev)
              if (ts_prev.tm_hour != ts_now.tm_hour or ts_prev.tm_mday != ts_now.tm_mday)  :
                _orig = delta_delivered-delta_received
                time_on_the_hr = time_now - ts_now.tm_min*60 - ts_now.tm_sec
                #print "1 {2:0.4f} {2:0.4f} {2:0.4f}".format(time_now, time_prev, time_on_the_hr);
                while time_prev < time_on_the_hr :
                    ts_prev = time.localtime(time_prev)
                    time_to_nh = (60-ts_prev.tm_min)*60 + (61-ts_prev.tm_sec)
                    time_diff = time_now - time_prev

                    pdelta_received = min(delta_received*time_to_nh/time_diff, delta_received)
                    pdelta_delivered= min(delta_delivered*time_to_nh/time_diff, delta_delivered)

                    hour_delta_received += pdelta_received
                    hour_delta_delivered += pdelta_delivered

                    if to_stdout:
                      print ("* hour (apportioned {4:0.4f})\t {0:2d}\treceived={1:0.4f}\tdelivered={2:0.4f}: {3:.4f}"\
                        .format(ts_prev.tm_hour, hour_delta_received,
                                hour_delta_delivered,
                                (hour_delta_delivered - hour_delta_received), _orig))

                    if (self.queue_db != None ):
                        self.queue_db.put(["8568062",time.strftime("%Y-%m-%d %H:00:01", ts_prev), (hour_delta_delivered - hour_delta_received)])

                    delta_received -= pdelta_received
                    delta_delivered -= pdelta_delivered

                    time_prev += time_to_nh
                    hour_delta_received = 0
                    hour_delta_delivered= 0

            hour_delta_received += delta_received
            hour_delta_delivered += delta_delivered

            if to_stdout:
              print ( "{0}\t{1:.4f}\t{2:0.4f}\t{3:.4f}\t{4:0.4f}".format(
                time.strftime("%Y-%m-%d %H:%M:%S", ts_now),
                reading_received,
                delta_received,
                reading_delivered,
                delta_delivered))

            if (x == total):
                if to_stdout:
                  print( "* hour {0:2d}\treceived={1:0.4f}\tdelivered={2:0.4f}: {3:.4f}"\
                    .format(ts_now.tm_hour, hour_delta_received,
                                hour_delta_delivered,
                                (hour_delta_delivered - hour_delta_received)))
                if (self.queue_db != None ):
                    self.queue_db.put(["8568062",time.strftime("%Y-%m-%d %H:00:01", ts_now), (hour_delta_delivered - hour_delta_received)])

            time_prev = time_now



    def run(self):
        #self.eg.set_fast_poll(frequency="0x01", duration="0x0F")
        #r = self.eg.get_fast_poll_status()
        #print r
        
        while True:
          try:
            #r = self.getEagle().get_instantaneous_demand()
            r = self.getEagle().get_device_data()
            self.logger.debug("Reading the meter ... %s", r)
            ni = r['NetworkInfo']
            id = r['InstantaneousDemand']
            if ( ni['Status'] == "Connected" ):
                kws = calc_kws(id)
                self.timeOfLastReading = time.time()
                if (self.timeOfFailure >= 0 and self.timeOfReconnection < 0 ):
                    self.timeOfReconnection = self.timeOfLastReading
                    self.logger.info("Established connection to meter at %s ... will refresh data soon", time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(self.timeOfReconnection)))

                # If we have reconnected check to see if we should attempt to recover
                # data lost while we had no connection
                if ( self.timeOfFailure >= 0 and self.timeOfReconnection >= 0 ):
                    _hourNext = self.timeOfReconnection - (self.timeOfReconnection % 3600) + 3600
                    self.logger.debug("Waiting to refresh ... Now: %s, Next Hour: %s", 
                                     time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(self.timeOfLastReading)), 
                                     time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(_hourNext)))
                    if ( self.timeOfLastReading > _hourNext + 5*60):
                        # figure out midnight of day before reconnection
                        _localtime = time.localtime(self.timeOfReconnection)
                        _midnight = self.timeOfReconnection - 24*60*60 - _localtime[3]*60*60 - _localtime[4]*60 - _localtime[5]
                        if (_midnight < 0 ):
                            _midnight = 0

                        try:
                            self.logger.info("Refreshing meter data starting at %s ...", time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(_midnight)))
                            self.summarize_history_data_by_hour(_midnight, None, to_stdout=False)
                        
                            # If we are successful reset indication of failed connection
                            self.timeOfFailure = -1.0
                        except Exception, e:
                            self.logger.warning("Failed to summarize data")
                            self.Logger.warning(str(e))
            else:
                kws = 0.0
                if ( self.timeOfFailure < 0 ):
                    self.timeOfFailure = time.time()
                self.timeOfReconnection = -1
                self.logger.warning("Meter not connected to network: %s", ni['Status'])


            if (kws != self.kws ):                        
                self.logger.debug("Meter reads: %f", kws)
                self.kws = kws

                if ( self.queue_readings != None ):
                    #self.queue_readings.put([id['MeterMacId'],
                    self.queue_readings.put(["8568062",
                                             to_epoch_1970(id['TimeStamp']),
                                             kws])
                else :
                    print_instantdemand(id)

            else:
                self.logger.debug("Meter reading unchanged from previous reading")

            time.sleep(1)
          except Exception, e:
            if (self.timeOfFailure < 0 ):
                self.timeOfFailure = time.time()
            self.timeOfReconnection = -1
            self.logger.warning("Failed to read the meter. Will try again ...")
            self.logger.warning(str(e))
            if ( self.queue_readings != None ):
                self.queue_readings.put(["8568062", time.time(), 0])
                
            time.sleep(5)
            #time.sleep(60)
        

if __name__ == '__main__':
    # create custom argument parsing
    parser = argparse.ArgumentParser(description="Talks to BC Hydro meter")

    parser.add_argument("-s", "--startdate", dest="start_date",
                    default=None,
                    help="Starting date for history (%Y-%m-%d)")

    parser.add_argument("-e", "--enddate", dest="end_date",
                    default=None,
                    help="Ending date for history (%Y-%m-%d)")

    # read config file
    cfg = config.config(parser=parser)
    cfg.setLogging()

    meter = Meter(cfg)
    
    if ( meter.getEagle() != None ):
        r = meter.getEagle().get_device_data()
        meter.logger.debug("Getting device data from the meter ... %s", r)

        calc_kws(r['InstantaneousDemand'])
        print_instantdemand(r['InstantaneousDemand'])
        print

        print_currentsummation(r['CurrentSummation'])
        print

    if cfg.results.start_date != None:
        print "start: " + cfg.results.start_date
        if cfg.results.end_date != None:
            print "end: " + cfg.results.end_date
        meter.summarize_history_data_by_hour(cfg.results.start_date, cfg.results.end_date)
        print

    meter.run()
    
    exit(0)
