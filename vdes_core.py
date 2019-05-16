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


def cmp(a, b):
    return (a > b) - (a < b)


class vDES:
    '''

    vDES: {
        devices: {
            devID: ->Device(
                        devID: (int)
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
    policyId =  "org.nrg5:NORM0001"
    thing_prefix = "org.nrg5:NORM"
    P_feature_name = "ActivePower"
    Q_feature_name = "ReactivePower"
    setpoint_p_tolerance = 0.1
    setpoint_q_tolerance = 0.1

    max_time_gap = 60  # seconds

    def __init__(self, _vmcmurl, user, password):
        self.vmcmurl = _vmcmurl
        self.auth = (user, password)
        self.devices = {}  # devicsa are stored in device dict and linked in lvgroups
        self.lvgroups = {}  # dict of groups, key is device id, value is device dict
        self.groups_changeflag = {}  # dict to keep trace of changes in the groups, used by the aggregator
        # todo: change groups_changeflag to last_update arg of lvgroup (add timestamp in lvgroup)
        self.lock = threading.Lock()

        # open req session to eclipse ditto
        self.ditto = requests.Session()
        self.ditto.auth = requests.auth.HTTPBasicAuth(user, password)

        # if not self._check_ditto_policy():
        #     exit(-1)

        if not self._check_ditto_things():
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

    def _check_ditto_things(self):
        r = self.ditto.get(url=self.vmcmurl + "/api/2/things?ids=org.nrg5:*")
        if r.ok:
            logger.info("{} {}".format(r.status_code, r.reason))
            return True
        else:
            logger.error("{} {}".format(r.status_code, r.reason))
            exit(-1)

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

    def send_message_to_dev(self, devId, jmsg):
        msg = json.dumps(jmsg)
        # if devId != jmsg['devId']:
        #     logger.error("devId doesn't match the data content")
        #     return -1
        thingId ="{}{:04X}".format(self.thing_prefix, devId)
        logger.debug("sending to {}: {}".format(devId, msg))

        r = self.ditto.post(url=self.vmcmurl + "/api/2/things/"+thingId+"/inbox/messages/setpoint")
        if r.ok:
            logger.info("{} {}".format(r.status_code, r.reason))
            return 0
        else:
            logger.error("{} {}".format(r.status_code, r.reason))
            return -1
        pass

    def _get_setpoint_deltas(self, groupId, P, Q):

        if groupId not in self.lvgroups:
            return None, None, None

        grp_feats_obj = self.__sum_group_features(groupId)
        group = self.lvgroups[groupId]

        if self.P_feature_name in grp_feats_obj:
            dP = P - grp_feats_obj[self.P_feature_name].value
        else:
            logger.warning("No feature found for active power P with name '{}'".format(self.P_feature_name))
            dP = P

        if self.Q_feature_name in grp_feats_obj:
            dQ = Q - grp_feats_obj[self.Q_feature_name].value
        else:
            logger.warning("No feature found for reactive power Q with name '{}'".format(self.Q_feature_name))
            dQ = Q

        return dP, dQ

    def _get_availble_flexibility(self, devId, feature, sign):
        if devId not in self.devices:
            return None, None, None

        device = self.devices[devId]
        flex = 0

        if feature in device.features:
            if sign > 0: # flexibility to increase
                flex = device.features[feature].maxval - device.features[feature].value
            else:
                if sign < 0:  # flexibility to decrease (must be negative):
                    flex = device.features[feature].minval - device.features[feature].value
        else:
            logger.warning("No feature found in {} for '{}'".format(devId, feature))
            flex = 0

        unit = ""
        if flex:
            unit = device.features[self.P_feature_name].units

        logger.debug("dev {}, has {}{} flexibility for feature '{}'".format(devId, flex, unit, feature))

        return flex


    def _get_new_setpoint(self, devId, feature, delta):
        if devId not in self.devices:
            return None

        device = self.devices[devId]
        sp = None

        if feature in device.features:
            if delta > 0: # flexibility to increase
                if delta >= (device.features[feature].maxval - device.features[feature].value):
                    sp = device.features[feature].value + delta
            else:
                if delta < 0:  # flexibility to decrease (must be negative):
                    if delta >= (device.features[feature].minval - device.features[feature].value):
                        sp = device.features[feature].value + delta
        else:
            logger.warning("No feature found in {} for '{}'".format(devId, feature))
            sp = None

        unit = ""
        if sp:
            unit = device.features[self.P_feature_name].units

        logger.debug("new setpoint for feature '{}' in dev {}: {}{}".format(feature, devId, sp, unit))

        return sp

    def _allocate_power_deltas(self, groupId, dP, dQ):
        if groupId not in self.lvgroups:
            logger.error("group not in list")
            return None
        group = self.lvgroups[groupId]

        Ptba = dP # active  to be assigned
        Qtba = dQ # reactive power to be assigned

        power_allocation = {}

        # for dev in group.devs:
        #     power_allocation[dev] = {}
        #     power_allocation[dev]['P'] = self._get_new_setpoint(dev, self.P_feature_name, dP)  # return the P setpoint given a P delta
        #     logging.debug("Allocated {} Active Power to dev {}. Remaining {}".format(dP, dev, 0))
        #     power_allocation[dev]['Q'] = self._get_new_setpoint(dev, self.Q_feature_name, dQ)  # return the P setpoint given a P delta
        #     logging.debug("Allocated {} Active Power to dev {}. Remaining {}".format(dP, dev, 0))

        #TODO add meaningful algorithm to distribute power delta

        power_allocation = {}
        for dev in group.devs:
            power_allocation[dev] = {}
            if abs(Ptba) > self.setpoint_p_tolerance:
                aPf  = self._get_availble_flexibility(dev, self.P_feature_name, cmp(dP,0)) # return the power that could be allocated according to the sign (1: positive, -1=negative)
                if aPf is not 0:
                    if abs(Ptba) > abs(aPf):
                        Pd = Ptba
                    else:
                        Pd = aPf
                    power_allocation[dev]['P'] = self._get_new_setpoint(dev, self.P_feature_name, Pd) # return the P setpoint given a P delta
                    Ptba = Ptba - Pd
                    logging.debug("Allocated {} Active Power to dev {}. Remaining {}".format(Pd, dev, Ptba))
                    # the power allocation values are dictionaries with a P and Q keys indicating the future setpoints for P and Q

            if abs(Qtba) > self.setpoint_q_tolerance:
                aQf = self._get_availble_flexibility(dev, self.Q_feature_name, cmp(dQ,0))  # return the power that could be allocated according to the sign (1: positive, -1=negative)
                if aQf is not 0:
                    if abs(Qtba) > abs(aQf):
                        Qd = Qtba
                    else:
                        Qd = aQf
                    power_allocation[dev]['Q'] = self._get_new_setpoint(dev, self.Q_feature_name, Qd)  # return the P setpoint given a P delta
                    Qtba = Qtba - Qd
                    logging.debug("Allocated {} Rective Power to dev {}. Remaining {}".format(Qd, dev, Qtba))

        if abs(Ptba) > self.setpoint_p_tolerance :
            logging.warning("Not enough Active power flexibility. Remaining {}".format(Ptba))
            return -1
        if abs(Qtba) > self.setpoint_q_tolerance:
            logging.warning("Not enough Reactive power flexibility. Remaining {}".format(Qtba))
            return -1

        return power_allocation


    def resolve_aggregated_setpoint(self, groupId, P, Q, ts):
        #FIXME how does timestamp influence this?
        [deltaP, deltaQ] = self._get_setpoint_deltas(groupId, P, Q)
        logging.debug("new setpoint differ from current states by dP: {}, dQ: {}".format(deltaP, deltaQ))

        # FIXME maybe Check if enough power flexibility is available in the group
        # maybe not, since i cna still try to allocata the most I can and then notify tvESR that not everything has been done

        power_allocation = self._allocate_power_deltas(groupId, deltaP, deltaQ)
        '''
        power_allocation should be a dictionary where the keys are the device id selected to enforce the setpoint.
        The values are composed by dict with a "P" and a "Q" keys, indicating the new power setpoint (not delta) for the 
        device
        '''
        if power_allocation is None:
            logger.error("Unable to allocate dP: {}, dQ: {} in group {}".format(deltaP, deltaQ, groupId))
            return 2, "Unable to allocate dP: {}, dQ: {} in group {}".format(deltaP, deltaQ, groupId)

        for dev in power_allocation:
            # prepare json object
            jmsg = {
                'devId': "0x{:04X}".format(dev),
                'P': power_allocation[dev]['P'],
                'Q': power_allocation[dev]['Q'],
                'timestamp': ts
            }

            if self.send_message_to_dev(dev, jmsg) is not 0:
                logger.error("failed sending message to device {}{:04X}".format(self.thing_prefix,dev))
                return 1, "failed sending message to device {}{:04X}".format(self.thing_prefix,dev)

        return 0, None

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




