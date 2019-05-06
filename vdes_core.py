import requests
from sseclient import SSEClient
import logging, coloredlogs
import threading
import copy
import json
from lvgroup import LVGroup
from feature import Feature
from device import Device

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG


class vDES:
    '''

    vDES: {
        devices: {
            devID: ->Device(
                        devID:
                        groupID:
                        position: {lat: , long: }
                        devtype:
                        features: ->Feature(
                                        name:
                                        value:
                                        units:
                                        last_updated:
                                    )
                     ),

            devID: ->Device(),
            devID: ->Device(),
            ...
        },

        lvgroups: {
            groupID: ->LVGroup(
                            groupId:
                            devices: {
                                devID: ->Device()
                                devID: ->Device()
                                ...
                            }
                        ),
            groupID: ->LVGroup(),
            groupID: ->LVGroup(),
            ...
        }
    }

    '''

    batt_devtype = "battery"
    char_sta_devtype = "charging_sta"
    ev_devtype = "ev"
    policyId =  "org.nrg5:NORMPOLICY"

    max_time_gap = 60  # seconds

    def __init__(self, _vmcmurl, user, password):
        self.vmcmurl = _vmcmurl
        self.auth = (user, password)
        self.devices = {}  # devicsa are stored in device dict and linked in lvgroups
        self.lvgroups = {}  # dict of groups, key is device id, value is device dict
        self.groups_changeflag = {}  # dict to keep trace of changes in the groups, used by the aggregator
        # todo: change groups_changeflag to last_update arg (add timestamp)
        self.lock = threading.Lock()

        # open req session to eclipse ditto
        self.ditto = requests.Session()
        self.ditto.auth = requests.auth.HTTPBasicAuth("demo1", "demo")

        if not self._check_ditto_policy():
            exit(-1)

        dev_list = self.get_vmcm_device_list(self.vmcmurl)
        if dev_list is not None:
            for dev in dev_list:
                self.load_device(dev)
        else:
            logger.info("no devices found, yet")
        # for g in self.lvgroups:
        #     logger.debug(json.dumps(self.lvgroups[g].to_json(), indent=4))
        pass

    def _check_ditto_policy(self):
        r = self.ditto.get(url=self.vmcmurl+"/api/2/policies/{}".format(self.policyId))
        if r.ok:
            logger.info("{} {}".format(r.status_code, r.reason))
            return True
        else:
            logger.error("{} {}".format(r.status_code, r.reason))
            exit(-1)

    def load_device(self, dev):
        devID = self._SSE_get_devID(dev)
        features = self._SSE_get_features(dev)
        attributes = self._SSE_get_attributes(dev)
        self._put_device(devID, features, attributes)
        pass

    def get_vmcm_device_list(self, vmcmurl):

        # send search request for field "devtype" battery or charging stations
        r = self.ditto.get(url=vmcmurl+'/api/2/search/things?filter=or(eq(attributes/devtype,"{}"),'\
                                  'eq(attributes/devtype,"{}"), eq(attributes/devtype,"{}"))'.format(self.batt_devtype,
                                                                                                     self.char_sta_devtype,
                                                                                                     self.ev_devtype))
        if not r.ok:
            logger.error("{} {}".format(r.status_code, r.reason))
            if r.status_code == 404:
                return None
            exit(-1)
        jdata = json.loads(r.text)
        dev_lst = jdata["items"]
        logger.debug(dev_lst)
        return dev_lst

    def _SSE_get_features(self, _jobj):
        jfeatures = _jobj["features"]
        rfeatures = {}

        for feat in jfeatures:
            try:
                assert ("properties" in jfeatures[feat])
                assert ("status" in jfeatures[feat]["properties"])
                assert ("maxval" in jfeatures[feat]["properties"])
                assert ("minval" in jfeatures[feat]["properties"])
                val = jfeatures[feat]["properties"]["status"]["value"]
                units = jfeatures[feat]["properties"]["status"]["units"]
                last_updated = jfeatures[feat]["properties"]["status"]["lastMeasured"]
                maxval = jfeatures[feat]["properties"]["maxval"]
                minval = jfeatures[feat]["properties"]["minval"]
                rfeatures[feat] = Feature(feat, val, units, last_updated, self.max_time_gap, maxval, minval)
                logger.debug("feat: {}, val: {}{}, time: {}".format(feat, val, units, last_updated))

            except AssertionError as e:
                logger.error("key error in feature: '"+feat+"': "+json.dumps(jfeatures[feat]))
                pass
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

    def __remove_device_from_group(self, devID):
        # retreive groupId from device
        groupID = self.devices[devID].groupID
        logger.debug("removing dev.{} from group.{}".format(devID, groupID))
        group = self.lvgroups[groupID]
        assert(isinstance(group, LVGroup))
        group.devs.pop(devID)

    def __link_device_to_group(self, devID):
        # retreive groupId from device
        groupID = self.devices[devID].groupID
        #link it to new group
        if groupID not in self.lvgroups:
            logger.debug("creating group{}".format(groupID))
            new_group = LVGroup(groupID)
            self.lvgroups[groupID] = new_group  # create a new group

        group = self.lvgroups[groupID]
        assert (isinstance(group, LVGroup))
        logger.debug("assigning dev.{} to group.{}".format(devID, groupID))
        group.devs[devID] = self.devices[devID]  # link into group dict
        pass

    def _put_device(self, devID, features, attributes):
        try:
            assert ("devtype" in attributes)
            assert ("groupId" in attributes)
            groupID = attributes["groupId"]
            if groupID == "":
                groupID = "unassigned"
            devtype = attributes["devtype"]
            assert(devtype is not None)

            # save the device info in memory, just update if existing
            self.lock.acquire()
            if devID in self.devices:
                dev = self.devices[devID]
                assert (isinstance(dev, Device))
                logger.debug("updating features on dev.{}".format(devID))
                if groupID != self.devices[devID].groupID:
                    self.__remove_device_from_group(devID)
                dev.put_features(features)
                dev.put_attributes(attributes)
                self.__link_device_to_group(devID)
            else:
                logger.debug("creating dev.{}".format(devID))
                new_dev = Device(devID, groupID, devtype, features)  # create device
                self.devices[devID] = new_dev  # add to dev dict
                self.__link_device_to_group(devID)

            self.groups_changeflag[groupID] = True

        except AssertionError as e:
            logger.error("skipping {} for not being complete".format(devID))
            pass
        finally:
            self.lock.release()

    def lvgroups_to_json(self, groupId="*"):
        jdata = {
            "groups": {}
        }
        if groupId == "*":
            for group in self.lvgroups:
                jdata["groups"][group] = self.lvgroups[group].to_json()
        else:
            if groupId in self.lvgroups:
                jdata["groups"][groupId] = self.lvgroups[groupId].to_json()

        return jdata

    def __sum_group_features(self, groupId):
        group = self.lvgroups[groupId]
        gr_feat_obj = {}
        for dev in group.devs:
            features = group.devs[dev].features
            for feat in features:
                if feat not in gr_feat_obj:
                    gr_feat_obj[feat] = copy.copy(features[feat])
                    logger.debug("created group feature from dev{}, val{} -> {}".format(dev, features[feat].value, gr_feat_obj[feat].to_json()))
                else:
                    gr_feat_obj[feat] = gr_feat_obj[feat]+features[feat]
                    logger.debug("added feature from dev{}, val{} -> {}".format(dev, features[feat].value, gr_feat_obj[feat].to_json()))

        return gr_feat_obj

    def __get_devtypes_count_grp(self, groupId):
        group = self.lvgroups[groupId]
        devtypes_dict = {}
        for dev in group.devs:
            devtype = group.devs[dev].devtype
            if devtype not in devtypes_dict:
                devtypes_dict[devtype] = 1
                logger.debug("addedd devtype {} from dev{}".format(devtype, dev))
            else:
                devtypes_dict[devtype] = devtypes_dict[devtype] +1
                logger.debug("+1 on devtype {} from dev{}".format(devtype, dev))
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
            logger.error("group "+groupId+" not found")
            raise KeyError

    def foreverloop(self):
        # connect to ditto through sse
        logger.info("subscribed to: "+self.vmcmurl+"/api/2/things/")
        messages = SSEClient(self.vmcmurl+"/api/2/things/", auth=self.auth)
        for msg in messages:
            if msg.data:
                logger.debug("event: {}. data: {}. id: {}. retry: {}".format(msg.event, msg.data, msg.id, msg.retry))
                jdata = json.loads(msg.data)
                self.load_device(jdata)
            # keep listening for events (new devices, new data)
            # update aggregated data every x minute
            pass




