import paho.mqtt.client as mqtt
import logging, coloredlogs
import requests
import json
import websocket
import threading

coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__.split('/')[-1])
logger.level = logging.DEBUG
# logger.getLogger("requests").setLevel(logger.WARNING)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.debug("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("vdes/data")
    logger.debug("subscribed to vdes/data")
    client.subscribe("/vMCM_Update")
    logger.debug("subscribed to vMCM_Update")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global ditto
    global policyId
    #logger.debug("rcvd: "+msg.topic+" "+str(msg.payload))
    jmsg=json.loads(msg.payload.decode("utf-8"))
    logger.debug("loaded: {}".format(json.dumps(jmsg), indent=2, sort_keys=True))
    thingId = "org.nrg5:NORM{}".format(jmsg["devID"])   # devID is a string
    logger.debug((thingId, policyId))

    jdata = {
        "thingId": thingId,
        "policyId": policyId,
        "attributes": {
            "firmware": "v0.1",
            "software": "v0.1",
            "manufacturer": "Sorbonne Universite",
            "devtype": "",
            "groupId": ""
        },
        "features": {}
    }

    if "devtype" in jmsg["attributes"]:
        logger.debug("devtype: {}".format(jmsg["attributes"]["devtype"]))
        jdata["attributes"]["devtype"] = jmsg["attributes"]["devtype"]
    else:
        logger.error("no devtype field")

    if "groupId" in jmsg["attributes"]:
        jdata["attributes"]["groupId"] = jmsg["attributes"]["groupId"]
    else:
        logger.error("no groupID field")

    logger.debug("features: {}".format(jmsg["features"]))
    for key in jmsg["features"]:
        logger.debug("[{}]:{}".format(key, jmsg["features"][key]))
        jdata["features"][key] = jmsg["features"][key]

    # fetch things ID
    # searchfilter='eq(attributes/nrg5id,{})'.format(jdata["attributes"]["nrg5id"])
    # logging.DEBUG("searchfilter: {})'.format(searchfilter)
    # r = ditto.get(url="https://ditto.eclipse.org/api/2/things", )
    # if r.ok && r.json[items]:
    #     thingid = r.json["items"][0]["thingId"]cd ..
    #     logger.debug("thingID: {})'.format(thingid)
    # else
    logger.debug("putting: {}".format(json.dumps(jdata), indent=2, sort_keys=True))
    r = ditto.put(url="https://ditto.eclipse.org/api/2/things/{}".format(thingId), data=json.dumps(jdata))
    logger.debug(r)
    logger.debug(r.text)

def ws_on_message(ws, message):
    logger.debug(message)

def ws_on_error(ws, error):
    logger.error(error)

def ws_on_close(ws):
    logger.info("### ws_closed ###")

def ws_on_open(ws):
    logger.info("### ws_opened ###")


local_mqtt_host = "localhost"
local_mqtt_port = 1883
# dittourl="http://localhost:8080"
dittourl="http://ditto.eclipse.org"
#wshost="localhost:8080"
wsversioni = "/2"

if __name__ == "__main__":

    # connect to local MQTT broker to communicate with other clients in the device
    mqttclient = mqtt.Client()
    mqttclient.on_connect = on_connect
    mqttclient.on_message = on_message
    mqttclient.connect(local_mqtt_host, local_mqtt_port, 60)

    # open req session to eclipse ditto
    ditto = requests.Session()
    ditto.auth=requests.auth.HTTPBasicAuth("demo1", "demo")

    # create policy
    global policyId
    policyId =  "org.nrg5:NORMPOLICY"
    jpolicy = {
        "policyId": policyId,
        "entries": {
            "DEFAULT": {
                "subjects": {
                    "nginx:demo1": {
                        "type": "generated"
                    }
                },
                "resources": {
                    "policy:/": {
                        "grant": [
                            "READ",
                            "WRITE"
                        ],
                        "revoke": []
                    },
                    "thing:/": {
                        "grant": [
                            "READ",
                            "WRITE"
                        ],
                        "revoke": []
                    },
                    "message:/": {
                        "grant": [
                            "READ",
                            "WRITE"
                        ],
                        "revoke": []
                    }
                }
            }
        }
    }
    r = ditto.put(url=dittourl+"/api/2/policies/{}".format(policyId), data=json.dumps(jpolicy))
    if r.ok:
        logger.info("policy check - OK")
        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        threading.Thread(target=mqttclient.loop_forever).start()
    else:
        logger.error("{} {} - Unable to connect to eclipse ditto. Exiting".format(r.status_code, r.reason))
        exit(-1)

    while True:
        pass

    ### connect to ditto via websocket
    # websocket.enableTrace(True)  # for debug prompt
    # wsurl = "ws://"+wshost+"/ws/2"
    #
    # ws = websocket.WebSocketApp(wsurl,
    #                             on_message=ws_on_message,
    #                             on_error=ws_on_error,
    #                             on_close=ws_on_close,
    #                             on_open=ws_on_open)
    # # add auth
    # dummy = requests.Request()
    # ws.header.append("Authorization: {}".format(ditto.auth(dummy).headers['Authorization']))
    # ws.run_forever(origin="vmcm_client")

