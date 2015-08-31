"""MQTT script run on raspberry Pi."""
#! /usr/bin/python

# Notes:
# 
# To install python/mosquitto library run following line in shell
# (this assumes you have your piface installed and the python library 
#  installed too)
#
#apt-get install python-mosquitto
#
# TODO:
# - respond to request for current values

#Standard Library Imports
import sys
import time
import os
import logging
import re
from threading import Thread
from Queue import Queue
from Queue import Empty

#Third Party Imports
import paho.mqtt.client as paho

#Local Application/Library Specific Imports
import config
#import gpio

class mqtt(Thread):
    """Class to connect/communicate with MQTT server"""

    def __init__(self, cfg, publish_queue = None, on_msg_queue = None):
        """Class Constructor ... called when object instance created.
    
           Arguments:
               self - object being created
               cfg  - pointer to config.config class instance
        """

        Thread.__init__(self)

        self.logger = cfg.setLogging(self.__class__.__name__)

        self.current_time = time.time()

        self.cfg = cfg
        self.on_msg_queue = on_msg_queue
        self.publish_queue = publish_queue
        
        # Figure out the details of the MQTT Server to talk to
        cfg.setdefault("Mqtt.Server", default = "localhost") 
        cfg.setdefault("Mqtt.Port", default = 1883)
        cfg.setdefault("Mqtt.Identity_pub", default = "xxx_PUB")
        cfg.setdefault("Mqtt.Identity_rcv", default = "xxx_RCV")
        #self.topicheader = topicheader+ '/' + self.ident
        cfg.setdefault("Mqtt.Topic", default = "xxx")

        # setup as MQQT client
        self.mos = paho.Client(cfg["Mqtt.Identity_pub"])
        self.mos.will_set(cfg["Mqtt.Topic"] +"/" +  cfg["Mqtt.Identity_pub"] + "/DOWN",0)
        self.mos.on_connect = self.on_connect
        self.mos.on_disconnect = self.on_disconnect
        self.mos.on_message = self.on_message # register for callback

        while (self.connect() == False ):
            self.logger.info ("Trying to connect again ...")
            time.sleep(5)

        # storage for latest data points
        self.data_points = {}
        
    #
    # Method: connect
    #
    # Connect to MQTT server
    #
    # Arguments:
    #    self - pointer to self
    #
    def connect(self, reconnect = False):
        try:
            if (reconnect):
                self.mos.reconnect()
            else:
                self.mos.connect(self.cfg["Mqtt.Server"], self.cfg["Mqtt.Port"])
        except:
            e = sys.exc_info()[0]
            self.logger.warning("Connection Failed with error: %s", str(e))
            #raise
            return False
        self.logger.info("connected to mqtt server at %s:%d",
                         self.cfg["Mqtt.Server"], self.cfg["Mqtt.Port"])
        return True
    
    #
    # Method: run
    #
    # Continuous loop to check for outbound MQTT messages (do I need to
    # publish anything)
    #
    # Arguments:
    #    self - pointer to self
    #
    def run(self):
        
        while (True):
            self.logger.debug("Checking ...")
            self.mos.loop(0)
            #self.logger.debug("Woke up ...")

            if (self.publish_queue != None ):

              try:
                pub=self.publish_queue.get(True, 1)
                self.logger.debug("Item in queue ...")
                strHeader = self.cfg["Mqtt.Topic"] + "/" + \
                            self.cfg["Mqtt.Identity_pub"] + "/" + \
                            pub[0] + "/" + str(pub[1])
                self.mos.publish(strHeader, pub[2])
                self.publish_queue.task_done()

                # Store last readings in case anybody asks
                self.data_points[pub[0]] = pub

                self.logger.debug("Published msg: %s", strHeader)

              except Empty:
                #Handle empty queue here
                pass


    # The callback for when the client receives a CONNACK response
    # from the server.
    def on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connected with result code: %s", str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #_str = self.cfg["Mqtt.Topic"] + "/" + self.cfg["Mqtt.Identity_rcv"] + "/current"
        _str = self.cfg["Mqtt.Topic"] + "/" + self.cfg["Mqtt.Identity_rcv"] + "/#"
        self.mos.subscribe(_str, 0) # get all messages for me
        #self.mos.subscribe("#", 0) # get all messages
        self.logger.info("subscribed to %s", _str)

        # Set a will so that DOWN will be sent if we die and send an 'UP' message now
        _strHeader = self.cfg["Mqtt.Topic"] + "/" + \
                    self.cfg["Mqtt.Identity_pub"] 
        self.mos.publish(_strHeader + "/UP",0)
        
        self.logger.info("Set will and published 'UP'")

    def on_disconnect(self, userdata, flags, rc):
        if (rc):    # unexpected disconnection ... try to reconnect
            self.logger.warning("Disconnected with result code: %s", str(rc))

            self.logger.info("Trying to reconnect ...")
            while (self.connect(True) == False ):
                self.logger.info ("Failed to reconnect.  Will sleep and try again ...")
                time.sleep(5)
 
    #
    # Method: on_message
    #
    # callback method executed when message received from MQTT server
    #
    # Arguments:
    #    self - pointer to self
    #    obj - ???
    #    msg - ???
    #
    def on_message(self, xxx,  obj, msg):
        self.logger.info("Msg received: %s - %s", msg.topic, msg.payload)

        _topic = msg.topic.split("/")
        if ( _topic[len(_topic)-1] == "current" ):
            _str = self.cfg["Mqtt.Topic"] + "/" + \
                        self.cfg["Mqtt.Identity_pub"] + "/"

            # Send out an 'I AM ALIVE' ...
            self.mos.publish(_str + "UP", 0);

            # only respond to request for current values
            for point in self.data_points:
                pub = self.data_points[point]
                strHeader = _str + pub[0] + "/" + str(pub[1])
                self.logger.debug("Publishing(" + str(len(self.data_points)) +") " + strHeader + ": " + str(pub[2]))
                self.mos.publish(strHeader, pub[2])

        elif ( self.on_msg_queue != None ):
            self.on_msg_queue.put([_topic[len(_topic) -1], msg.payload])

        self.logger.debug("Finished")


    def __del__(self):
        self.mos.disconnect()

#
# MAIN CODE - THIS IS WHAT IS RUN IF YOU TYPE 'python mqtt.py' in a shell
#
if __name__ == '__main__':
    # read config file
    cfg = config.config()
    cfg.setLogging()

    queueMqttPub = Queue()

    conn = mqtt(cfg, publish_queue = queueMqttPub)
    conn.daemon = True
    conn.start()

    xxx = 0

    while (True):
        logging.info("Adding to queue");
        queueMqttPub.put(["XXX", 0, xxx])
        xxx = xxx+5
        time.sleep(5)

    logging.info("Finished normally")
