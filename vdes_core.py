import requests
from sseclient import SSEClient
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.DEBUG)

class Property:
    value = 0
    last_updated = datetime.min

    def __init__(self, _value, _last_updated):
        self.value = _value
        self.last_updated = _last_updated


class Device:
    devID = ""
    devtype = ""
    properties = {}  # doct where key is property name (string)

    def __init__(self, _devID, _devtype, **kwproperties):
        self.devID = _devID
        self.devtype = _devtype
        for p in kwproperties:
            self.properties[p] = kwproperties[p]


class vDES:
    devices = {}    # dict of devices, key is device id, value is device instance
    lvID = ""
    mcmurl=""
    auth = ""

    def __init__(self, _mcmurl, user, password):
        self.mcmurl = _mcmurl
        self.auth = (user, password)
        pass

    def get_device_list(self, url):
        logging.warning(__name__+" not implemented.")
        pass

    def _SSE_get_features(self, msg):
        logging.warning(__name__ + " not implemented.")
        pass

    def _SSE_get_attributes(self, msg):
        logging.warning(__name__ + " not implemented.")
        pass

    def _put_device(self, devID, features, attributes):
        logging.warning(__name__ + " not implemented.")
        pass

    def _SSE_get_devID(self, _json):
        try:
            jdata = json.loads(_json)
            thingID = jdata["thingId"]
            devID = "0x"+thingID.split("NORM")[1]
            logging.debug("message regarding {:s}".format(devID))
            return int(devID, 16)
        except ValueError as err:
            logging.error("invalid json format")
            raise

    def foreverloop(self):
        # connect to ditto through sse

            messages = SSEClient(self.mcmurl, auth=self.auth)
            for msg in messages:
                logging.debug(msg)
                logging.debug("event: {}\n data: {}\n id: {}\n retry: {}".format(msg.event, msg.data, msg.id, msg.retry))
                if msg.data:
                    devID = self._SSE_get_devID(msg.data)
                    features = self._SSE_get_features(msg)
                    attributes = self._SSE_get_attributes(msg)
                    self._put_device(devID, features, attributes)
                # keep listening for events (new devices, new data)
                # update aggregated data every x minute
                pass
