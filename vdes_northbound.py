import sys, os
import logging
from flask import Flask, abort
from flask_restful import Api, Resource, reqparse
sys.path.append(os.path.abspath(os.path.join("..")))
from vdes_core import vDES
import traceback

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
    api.add_resource(Devices, "/groups/<string:groupId>/devices/<string:devId>")

    logging.debug("Starting REST interface on port {}".format(api_port))
    app.run(port=api_port)



class Groups(Resource):

    def get(self, groupId="*"):
        global vdes
        logging.warning("Received GET request, not Implemented")
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

    def post(self, groupId):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        global vdes
        logging.warning("Received POST request, not Implemented")
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()

    def put(self, groupId):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        logging.warning("Received PUT request, not Implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()


    def delete(self, groupId):
        logging.warning("Received DELETE request, not implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()


class GroupAggregator(Resource):

    def get(self, groupId):
        global vdes
        logging.warning("Received GET request, not Implemented")
        vdes.lock.acquire()
        try:
            if groupId in vdes.lvgroups:
                return vdes.get_lvgroup_aggregated(groupId)
            else:
                abort(404)
        finally:
            vdes.lock.release()

    def post(self, groupId):
        logging.warning("Received POST request, not Implemented")
        return 501

    def put(self, groupId):
        plogging.warning("Received PUT request, not Implemented")
        return 501

    def delete(self, groupId):
        logging.warning("Received DELETE request, not Implemented")
        return 501


class Devices(Resource):

    def get(self, str_ID):
        global vdes
        logging.warning("Received GET request, not Implemented")
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()

    def post(self, str_ID):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        global vdes
        logging.warning("Received POST request, not Implemented")
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()

    def put(self, str_ID):
        prs = reqparse.RequestParser()
        a = prs.parse_args()
        logging.warning("Received PUT request, not Implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()


    def delete(self, str_ID):
        logging.warning("Received DELETE request, not implemented")
        global vdes
        vdes.lock.acquire()
        try:
            return 501
        finally:
            vdes.lock.release()
