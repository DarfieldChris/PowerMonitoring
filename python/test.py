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
#import sys, serial, select, time, datetime, logging, glob, socket, struct, csv, MySQLdb
import sys, serial, select, time, datetime, logging, glob, socket, struct, csv, MySQLdb
from threading import Thread
from Queue import Queue
from socket import AF_INET, SOCK_DGRAM

#Third Party Imports

#Local Application/Library Specific Imports
import config
import mqtt
import arduino


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
    queueMqttOnMsg = Queue()

    # setup Arduino thread

    ports=glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/tty.usbserial*")
    logging.info("Will connect to Arduino using ports: %s" % ports)

    ard = arduino.Arduino(cfg, ports=ports, queueToArduino=queueMqttOnMsg)

    # Setup Mqtt client thread
    mqtt_client = mqtt.mqtt(cfg)
    mqtt_client.publish_queue = queueMqttPub
    mqtt_client.on_msg_queue = queueMqttOnMsg
    mqtt_client.daemon = True
    mqtt_client.start()
 
    # start main thread of execution
    try :
      ard.run()
    except serial.SerialException :
      logging.error("Disconnected (Serial exception)")
    except IOError :
      logging.error("Disconnected (I/O Error)")
    except KeyboardInterrupt :
      print "Interrupt"
      exit(0)

