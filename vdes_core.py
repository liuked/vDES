import requests
from sseclient import SSEClient
import time
from datetime import datetime
import logging, coloredlogs, traceback
import threading
import copy
import json

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG

class Feature:
    name = ""
    value = 0
    units = ""
    last_updated = datetime.min

    def __init__(self, _name, _value, _units, _last_updated):
        self.name = _name
        self.value = _value
        self.units = _units
        self.last_updated = _last_updated

    def __add__(self, other):
        try:
            last_datetime = None
            assert (isinstance(other, Feature))
            last_datetime = datetime.fromtimestamp(max(self.__timestamp_from_date(), other.__timestamp_from_date()))

            assert(self.__is_summable(other))
            return Feature(self.name, self.value+other.value, self.units, last_datetime.strftime("%y-%m-%dT%H:%M:%S"))

        except AssertionError:
            logging.error("{} and {} are not summable".format(self.to_json(), other.to_json()))
            # return the most recent feature
            if last_datetime is not None and last_datetime == other.__timestamp_from_date():
                return self
            else
                return other


    def __timestamp_from_date(self):
        return time.mktime(datetime.strptime(self.last_updated, "%y-%m-%dT%H:%M:%S").timetuple())

    def __is_summable(self, other):
        last_timestamp = self.__timestamp_from_date()
        other_last_timestamp = other.__timestamp_from_date()
        samename = (self.name == other.name)
        sameunit = (self.units == other.units)
        timegap = abs(last_timestamp - other_last_timestamp)
        sametime = ( timegap < vDES.max_time_gap)
        logging.debug("[{}] samename? {}; sameunit? {}; sametime? {}(gap{})".format(self.name, samename, sameunit,sametime,timegap))
        return (samename and sameunit and sametime)

    def to_json(self):
        return {
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "last_updated": self.last_updated
        }


class Device:
    devID = ""
    groupID = ""
    position = { "lat": None, "long": None}
    devtype = ""
    features = {}  # dict where key is feature name (string)

    def __init__(self, _devID, _groupID, _devtype, _featuresdict):
        self.devID = _devID
        self.devtype = _devtype
        self.groupID = _groupID
        self.features = _featuresdict

    def to_json(self):
        jdata = {
            "devId": self.devID,
            "groupID": self.groupID,
            "position": self.position,
            "devtype": self.devtype,
            "features": {}
        }

        for feat in self.features:
            jdata["features"][feat] = self.features[feat].to_json()

        return jdata



class vDES:
    lvgroups = {}   # dict of groups, key is device id, value is device dict
    vmcmurl=""
    auth = ""
    batt_devtype = "battery"
    char_sta_devtype = "charging_sta"
    ev_devtype = "ev"
    lock = threading.Lock()
    max_time_gap = 60  # seconds

    def __init__(self, _vmcmurl, user, password):
        self.vmcmurl = _vmcmurl
        self.auth = (user, password)

        dev_list = self.get_vmcm_device_list(self.vmcmurl)
        assert(dev_list!=None)
        for dev in dev_list:
            self.load_device(dev)
        pass

    def load_device(self, dev):
        devID = self._SSE_get_devID(dev)
        features = self._SSE_get_features(dev)
        attributes = self._SSE_get_attributes(dev)
        self._put_device(devID, features, attributes)
        pass

    def get_vmcm_device_list(self, vmcmurl):
        # open req session to eclipse ditto
        ditto = requests.Session()
        ditto.auth = requests.auth.HTTPBasicAuth("demo1", "demo")

        # send search request for field "devtype" battery or charging stations
        r = ditto.get(url=vmcmurl+'/api/2/search/things?filter=or(eq(attributes/devtype,"{}"),'\
                                  'eq(attributes/devtype,"{}"), eq(attributes/devtype,"{}"))'.format(self.batt_devtype,
                                                                                                     self.char_sta_devtype,
                                                                                                     self.ev_devtype))
        jdata = json.loads(r.text)
        dev_lst = jdata["items"]
        logger.debug(dev_lst)
        return dev_lst


    def _SSE_get_features(self, _jobj):
        jfeatures = _jobj["features"]
        rfeatures = {}
        for feat in jfeatures:
            val = jfeatures[feat]["properties"]["status"]["value"]
            units = jfeatures[feat]["properties"]["status"]["units"]
            last_updated = jfeatures[feat]["properties"]["status"]["lastMeasured"]
            rfeatures[feat] = Feature(feat, val, units, last_updated)
            logger.debug("feat: {}, val: {}{}, time: {}".format(feat, val, units, last_updated))
        return rfeatures

    def _SSE_get_attributes(self, _jobj):
        attributes = _jobj["attributes"]
        for attr in attributes:
            logger.debug("attr: {}, val: {}".format(attr, attributes[attr]))
        return attributes

    def _SSE_get_devID(self, _jobj):
        try:
            thingID = _jobj["thingId"]
            devID = "0x"+thingID.split("NORM")[-1]
            logger.debug("message regarding {:s}".format(devID))
            return int(devID, 16)
        except ValueError as err:
            logger.error("invalid json format")
            raise

    def _put_device(self, devID, features, attributes):
        try:
            assert ("devtype" in attributes)
            assert ("groupId" in attributes)
            groupID = attributes["groupId"]
            if groupID == "":
                groupID = "unassigned"
            devtype = attributes["devtype"]
            assert(devtype is not None)

            self.lock.acquire()
            if groupID not in self.lvgroups:
                self.lvgroups[groupID] = {}  # create a new dict for devices

            new_dev = Device(devID, groupID, devtype, features)
            self.lvgroups[groupID][devID] = new_dev
            pass
        except AssertionError as e:
            logging.error("skipping {} for not being complete".format(devID))
            pass
        finally:
            self.lock.release()

    def __group_to_json(self, groupId):
        assert (groupId in self.lvgroups)
        jdata = {
            "groupId": groupId,
            "devices": {}
        }
        for dev in self.lvgroups[groupId]:
            jdata["devices"][dev] = self.lvgroups[groupId][dev].to_json()
        return jdata

    def lvgroups_to_json(self, groupId="*"):
        jdata = {
            "groups": {}
        }
        if groupId == "*":
            for group in self.lvgroups:
                jdata["groups"][group] = self.__group_to_json(group)
        else:
            if groupId in self.lvgroups:
                jdata["groups"][groupId] = self.__group_to_json(groupId)

        return jdata

    def __sum_group_features(self, groupId):
        group = self.lvgroups[groupId]
        gr_feat_obj = {}
        for dev in group:
            features = group[dev].features
            for feat in features:
                if feat not in gr_feat_obj:
                    gr_feat_obj[feat] = copy.copy(features[feat])
                    logging.debug("created group feature from dev{}, val{} -> {}".format(dev, features[feat].value, gr_feat_obj[feat].to_json()))
                else:
                    gr_feat_obj[feat] = gr_feat_obj[feat]+features[feat]
                    logging.debug("added feature from dev{}, val{} -> {}".format(dev, features[feat].value, gr_feat_obj[feat].to_json()))

        return gr_feat_obj

    def __get_devtypes_count_grp(self, groupId):
        group = self.lvgroups[groupId]
        devtypes_dict = {}
        for dev in group:
            devtype = group[dev].devtype
            if devtype not in devtypes_dict:
                devtypes_dict[devtype] = 1
                logging.debug("addedd devtype {} from dev{}".format(devtype, dev))
            else:
                devtypes_dict[devtype] = devtypes_dict[devtype] +1
                logging.debug("+1 on devtype {} from dev{}".format(devtype, dev))
        return devtypes_dict

    def get_lvgroup_aggregated(self, groupId):
        try:
            assert(groupId in self.lvgroups)
            grp_feats_obj = self.__sum_group_features(groupId)
            jdata = {
                "groupId": groupId,
                "features": {},
                "devtypes": {}
            }
            jdata["devtypes"] = self.__get_devtypes_count_grp(groupId)
            # serialization of feature dict
            for feat in grp_feats_obj:
                jdata["features"][feat] = grp_feats_obj[feat].to_json()
            return jdata
        except AssertionError:
            logging.error("group "+groupId+" not found")
            raise KeyError

    def foreverloop(self):
        # connect to ditto through sse
            messages = SSEClient(self.vmcmurl+"/api/2/things/", auth=self.auth)
            for msg in messages:
                if msg.data:
                    logger.debug("event: {}. data: {}. id: {}. retry: {}".format(msg.event, msg.data, msg.id, msg.retry))
                    jdata = json.loads(msg.data)
                    self.load_device(jdata)
                # keep listening for events (new devices, new data)
                # update aggregated data every x minute
                pass




