import os, sys
sys.path.append(os.path.abspath(os.path.join("..")))
from common.defines import *

import threading
from random import triangular
import socket
import logging
from time import sleep
import json
import struct


class esp:


    UNPLUGGED = 0
    CHARGING = 1
    SERVING = 2

    lock = threading.Lock()


    def __init__(self, id, lat, long, capacity, storage=0, **kwargs):
        self.id = id
        self.lat = lat
        self.long = long
        self.capacity = capacity
        self.storage = storage
        self.state = esp.UNPLUGGED
        self.properties = kwargs
        self.voltage = 0
        self.current = 0

    def __update_storage(self):

        step = 0

        if self.state == esp.UNPLUGGED:
            step = 0.100 + triangular(-0.050, 0.050)

        if self.state == esp.SERVING:
            step = self.capacity/2346.542 +  triangular(-self.capacity/4859.23, +self.capacity/1599.86)

        if self.state == esp.CHARGING:
            step = self.capacity/135.241 + triangular(-self.capacity/456.36, +self.capacity/892.3 )

        self.storage = self.storage + step

        if self.storage < 0:
            self.storage = 0

        if self.storage > self.capacity:
            self.storage = self.capacity

    def __connect_to_server(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        att = 1
        while att<10:
            try:
                self.server.connect((host, port))
                return 0
            except:
                sleep(3)
                logging.debug("Connecting error attempt {} - {}".format(att, (host, port)))
                att = att + 1

        logging.error("Unable to connect to server")
        return -1

    def __report_data(self):
        jdata = {
            'id': hex(self.id),
            'latitude': self.lat,
            'longitude': self.long,
            'capacity': self.capacity,
            'storage': self.storage,
            'properties': {
                'capunit': 'kWh',
                'nomvolt': '400',
                'nomcurr': '800'
            }
        }

        msg = json.dumps(jdata)
        logging.debug("Sending: {}".format(msg))
        with esp.lock:
            self.server.send(msg)
        logging.debug("SENT".format(msg))


    def __process_message(self, msg):
        try:
            assert isinstance(msg,msgcode)
            if msg == msgcode.CHARGE:
                self.state = esp.CHARGING
            if msg == msgcode.SERVE:
                self.state = esp.SERVING
            if msg == msgcode.UNPLUG:
                self.state = esp.UNPLUGGED

            logging.info("Received {} message... ESP state is now {}".format(msg.name, state))

        except AssertionError:
            logging.warning("unrecognized message received: {}".format(msg))


    def __commands_listener(self):
        while 1:
            msg = ''
            esp.lock.acquire()
            try:
                self.server.recv(2048)
            except socket.error as err:
                if err.errno == 11:
                    pass
                else:
                    raise
            finally:
                esp.lock.release()
                if msg:
                    self.__process_message(msg)

    def run(self, host, port):

        logging.info("Connecting to server at {}...".format((host,port)))
        if self.__connect_to_server(host, port) == -1:
            logging.error("ESP Startup FAILED. Shutting down...")
            exit(-1)
        sleep(1)
        logging.info("OK")

        logging.info("Starting command listener...")
        t = threading.Thread(target=self.__commands_listener)
        t.setDaemon(True)
        t.start()
        sleep(2)
        logging.info("OK...")

        logging.info("Starting data reporting...")
        sleep(1)

        while 1:
            logging.debug("Updating Storage ({})...".format(self.state))
            self.__update_storage()
            sleep(2)
            logging.debug("OK ({})...".format(self.storage))


            logging.info("Reporting data to server...")
            self.__report_data()
            sleep(1)
            logging.info("OK")

            sleep(3)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    esp(0x0001, 43.5, 46.0, 450, 200).run('127.0.0.1', 5050)