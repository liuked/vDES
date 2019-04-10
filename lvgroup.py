import json
import logging, coloredlogs

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG


class LVGroup:

    def __init__(self, groupId):
        assert (groupId is not "" and groupId is not None)
        self.groupId = groupId
        self.devs = {}  # dict where key is devId and value is link to Device instance
        #todo add timestamp last_modified

    def to_json(self):
        jdata = {
            "groupId": self.groupId,
            "devices": {}
        }
        for id in self.devs:
            jdata["devices"][id] = self.devs[id].to_json()
        return jdata