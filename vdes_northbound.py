import sys, os
from flask import Flask, abort
from flask_restful import Api, Resource, reqparse
sys.path.append(os.path.abspath(os.path.join("..")))
from vdes_core import vDES
import time
import logging, coloredlogs
import json

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG

def runrest(api_port, _vdes):
    global api
    global app
    global vdes
    assert (isinstance(_vdes, vDES))
    app = Flask(__name__)
    api = Api(app)
    vdes = _vdes

    api.add_resource(Groups, "/groups/<string:groupId>")
    api.add_resource(GroupAggregator, "/groups/<string:groupId>/aggregated")
    api.add_resource(GroupMessanger, "/groups/<string:groupId>/setpoint")
    api.add_resource(GroupAggregatorUpdate, "/groups/<string:groupId>/aggregated-update")
    api.add_resource(Devices, "/groups/<string:groupId>/devices/<string:devId>")

    logger.debug("Starting REST interface on port {}".format(api_port))
    app.run(port=api_port)


class Groups(Resource):

    def get(self, groupId="*"):
        global vdes
        vdes.lock.acquire()
        try:
            if groupId == "*":
                return vdes.lvgroups_to_json()
            if groupId in vdes.lvgroups:
                return vdes.lvgroups_to_json(groupId)
            else:
                abort(404)
        finally:
            vdes.lock.release()

    def put(self, groupId):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        logger.warning("Received PUT request, not Implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()


class GroupMessanger(Resource):

    '''
    vDES receives from vESR json data in the format:

    {
        id : "F1",(char 256)
        pSet : 400, (double)
        qSet : 200, (double)
        timestamp : 18472876918 (uint64)//unixtimestamp
    }

    //message for accumulated pSet and qSet for F1
    '''
    def put(self, groupId):
        prs = reqparse.RequestParser()
        prs.add_argument("id")
        prs.add_argument("pSet")
        prs.add_argument("qSet")
        prs.add_argument("timestamp")
        a = prs.parse_args()

        if a.id != groupId:
            logger.error("group id doesn't correspond")
            abort(400, descriprion="unmatching groupID")

        # prepare json object
        jmsg = {
            'devId': a.id,
            'P': a.pSet,
            'Q': a.qSet,
            'timestamp': a.timestamp
        }

        vdes.lock.acquire()
        try:
            if id in vdes.lvgroups:
                group = vdes.lvgroups[id]
                for dev in group.devs:
                    vdes.send_message_to_dev(dev, jmsg)

            else:
                abort(404)
        finally:
            vdes.lock.release()



class GroupAggregator(Resource):

    def get(self, groupId):
        global vdes
        vdes.lock.acquire()
        try:
            if groupId in vdes.lvgroups:
                return vdes.get_lvgroup_aggregated(groupId)
            else:
                abort(404)
        finally:
            vdes.lock.release()


class GroupAggregatorUpdate(Resource):

    def _is_updated(self, groupId):
        global vdes
        """
        Returns if resource is updated or it's the first time it has been requested.
    
        """
        return vdes.lvgroups[groupId].last_modified

    def get(self, groupId):
        """
        Returns content when the resource has changed after the request time
        """
        global vdes
        logger.warning("Received GET request, not Implemented")
        if groupId not in vdes.lvgroups:
            abort(404)

        # wait until update is available

        #todo: change check to last_modified lvgroup arg
        request_time = time.time()
        while not vdes.groups_changeflag[groupId]:
            time.sleep(0.5)

        vdes.lock.acquire()
        try:
            vdes.groups_changeflag[groupId] = False  # reset changeflag
            return vdes.get_lvgroup_aggregated(groupId)
        finally:
            vdes.lock.release()


class Devices(Resource):

    def get(self, str_ID):
        global vdes
        logger.warning("Received GET request, not Implemented")
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()

    def post(self, str_ID):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        global vdes
        logger.warning("Received POST request, not Implemented")
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()

    def put(self, str_ID):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        logger.warning("Received PUT request, not Implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()


    def delete(self, str_ID):
        logger.warning("Received DELETE request, not implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()
