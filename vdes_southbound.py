import os, sys
sys.path.append(os.path.abspath(os.path.join("..")))
from common.defines import *
from vdes_console import vdesShell

import socket
import threading
import struct
import logging
import json


class vdes(object):

    def __init__(self, host, port):


        ### open the request listener n specified port
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        logging.info("Listener is started on {}".format((host, port)))


    def listen(self):
        self.sock.listen(256)
        while True:
            try:
                client, address = self.sock.accept()
                logging.info("Receive connection from " + str(address))
                t = threading.Thread(target=self.__esp_listener, args=(client, address))
                t.setDaemon(True)
                t.start()

            except:
                raise

    def __esp_listener(self, esp, address):

        # receive data reporting messages
        # add client in list

        while True:
            try:
                msg = esp.recv(2048)
                if msg:
                    logging.debug("Received: {}".format(repr(msg)))
                    jdata = json.loads(msg)
                    logging.debug("Received: {}".format(repr(jdata)))
            except:
                raise

    def esp_unplug(self, args):
        logging.debug("Unplugging ESP #{}".format(args))


    def esp_charge(self, args):
        logging.debug("Charging ESP #{}".format(args))

    def esp_serve(self, args):
        logging.debug("Connecting ESP #{}".format(args))


if __name__ == "__main__":

    logging.basicConfig(file='vdes.log', level=logging.DEBUG)
    logging.info('Deploying vDES...')
    vdes1 = vdes('127.0.0.1', 5050)
    sleep(1)

    logging.info('Running ESP listener...')
    listener = threading.Thread(target=vdes1.listen())
    listener.setDaemon(True)
    listener.start()
    sleep(1)

    logging.info('Starting vDES CLI...')
    sleep(2)
    vdesShell().cmdloop()
