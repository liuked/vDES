import logging, coloredlogs
from feature import Feature

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG

class Device:

    def __init__(self, _devID, _groupID, _devtype, _featuresdict, _position={"lat": None, "long": None}):
        self.devID = _devID
        self.devtype = _devtype
        self.groupID = _groupID
        self.features = _featuresdict
        self.position = _position

    def put_features(self, features_dict):
        # add or update features into the dict
        for feat in features_dict:
            assert(isinstance(features_dict[feat], Feature))
            self.features[feat] = features_dict[feat]
        pass

    def put_attributes(self, attributes_dict):
        # add or update features into the dict
        if "groupId" in attributes_dict:
            self.groupID = attributes_dict["groupId"]
        if "devtype" in attributes_dict:
            self.devtype = attributes_dict["devtype"]
        pass

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