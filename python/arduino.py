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
import sys, serial, time, datetime, logging
from threading import Thread
from Queue import Queue
#from socket import AF_INET, SOCK_DGRAM

#Third Party Imports

#Local Application/Library Specific Imports
import config
import Calc
import DB
import HydroMeter
import mqtt
import Arduino

if __name__ == "__main__":
    # Setup basic logging ability until config data is parsed
    logging.basicConfig(format='%(levelname) -10s (%(threadName)-10s) %(asctime)s %(module)s:%(funcName)s[%(lineno)s] %(message)s',
                                                    level="INFO")

    # Procedure to query network time server for current time stamp
    #def getNTPTime(host = "pool.ntp.org"):
    #    port = 123
    #    buf = 1024
    #    address = (host,port)
    #    msg = '\x1b' + 47 * '\0'

    #    # reference time (in seconds since 1900-01-01 00:00:00)
    #    TIME1970 = 2208988800L # 1970-01-01 00:00:00

    #    # connect to server
    #    client = socket.socket( AF_INET, SOCK_DGRAM)
    #    client.sendto(msg, address)
    #    msg, address = client.recvfrom( buf )

    #    t = struct.unpack( "!12I", msg )[10]
    #    t -= TIME1970
    #    return t

    # read YML config data
    cfg = config.config()
    
    # Setup logging
    #logging.basicConfig(level=logging.DEBUG,
    #                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
    #                    )
    cfg.setLogging()

    #logging.info("Current time is %s" % time.ctime(getNTPTime()).replace("  "," "))

    # create queues to pass data between the different threads

    #
    # queueReadings
    #
    # Purpose: Queue of most recent device readings.
    #
    #          Each queue entry is a list containing:
    #           [name, timestamp, data]
    #               name      - the unique ID of the device reporting a reading
    #               timestamp - the timestamp of the reading in seconds from 1970.
    #               data      - the actual numeric float value of the reading
    # Example:
    #          ["HWT", 1232132, 0.37]
    #
    queueReadings  = Queue()

    #
    # queueToArduino
    #
    # Purpose: Queue to send control messages to Arduino.
    #
    #          Each queue entry is a list containing:
    #           [name, data]
    #               name      - the unique ID of the device to be controlled
    #               data      - the actual integer value of the control message
    # Example:
    #          ["HWTRelay", 0]
    #
    queueToArduino = Queue()
    
    #
    # queueDB
    #
    # Purpose: Queue of data points to by synched to permanent storage.
    #
    #          Each queue entry is a list containing:
    #           [name, time, data]
    #               name      - the unique ID of the device whose data is being synched
    #               time      - String representation of the time
    #               data      - the actual float value being synched
    # Example:
    #          ["HWT", "2015-07-30 23:00:00", 0.30]
    #    
    queueDB        = Queue()

    #
    # queueMqttPub
    #
    # Purpose: Queue of instantaneous updates to be broadcast via MQTT
    #
    #          Each queue entry is a list containing:
    #           [name, data]
    #               name      - the unique ID of the device
    #               timestamp - the timestamp of the reading in seconds from 1970.
    #               data      - the actual numeric float value of the reading
    # Example:
    #          ["HWT", 13123131231, 0.30]
    #
    queueMqttPub   = Queue()

    # Setup Mqtt client thread
    mqtt_client = mqtt.mqtt(cfg, publish_queue = queueMqttPub, on_msg_queue = queueToArduino)
    mqtt_client.daemon = True
    mqtt_client.start()

    # setup Arduino thread
    arduino = Arduino.Arduino(cfg, queueFromArduino=queueReadings, queueToArduino=queueToArduino)
 
    # setup calculation thread
    threadCalc = Calc.Calc(cfg, queueReadings=queueReadings, queueResults=queueDB, broadcast_queue = queueMqttPub)
    threadCalc.daemon = True
    threadCalc.start()

    # setup database thread
    updateDB = DB.UpdateDB(cfg, queueResults = queueDB)
    updateDB.daemon = True
    updateDB.start()

    # setup arduino scheduler thread
    ards = Arduino.ArdSchedule(cfg,queueToArduino)
    ards.initialize()
    ards.daemon = True
    ards.start()

    meter = HydroMeter.Meter(cfg, queue_readings = queueReadings)
    meter.daemon = True
    meter.start()

    # start main thread of execution
    try :
      arduino.run()
    except serial.SerialException :
      logging.error("Disconnected (Serial exception)")
    except IOError :
      logging.error("Disconnected (I/O Error)")
    except KeyboardInterrupt :
      logging.error( "Keyboard Interrupt")
      exit(0)
