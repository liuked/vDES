import paho.mqtt.client as mqtt
import logging
import requests
import json

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("vmcm")
    logging.debug("subscribed to vmcm")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global ditto
    global policyId
    #logging.debug("rcvd: "+msg.topic+" "+str(msg.payload))
    jmsg=json.loads(msg.payload.decode("utf-8"))
    logging.debug("loaded: {}".format(json.dumps(jmsg)))
    thingId = "org.nrg5:NORM{}".format(jmsg["devID"])   # devID is a string
    logging.debug((thingId, policyId))

    jdata = {
        "thingId": thingId,
        "policyId": policyId,
        "attributes": {
            "firmware": "v0.1",
            "software": "v0.1",
            "manufacturer": "Sorbonne Universite",
            "devtype": ''
        },
        "features": {}
    }

    logging.debug("devtype: {}".format(jmsg["attributes"]["devtype"]))
    jdata["attributes"]["devtype"] = jmsg["attributes"]["devtype"]
    logging.debug("features: {}".format(jmsg["features"]))
    for key in jmsg["features"]:
        logging.debug("[{}]:{}".format(key, jmsg["features"][key]))
        jdata["features"][key] = jmsg["features"][key]

    # fetch things ID
    # searchfilter='eq(attributes/nrg5id,{})'.format(jdata["attributes"]["nrg5id"])
    # logging.DEBUG("searchfilter: {})'.format(searchfilter)
    # r = ditto.get(url="https://ditto.eclipse.org/api/2/things", )
    # if r.ok && r.json[items]:
    #     thingid = r.json["items"][0]["thingId"]
    #     logging.debug("thingID: {})'.format(thingid)
    # else
    logging.debug("putting: {}".format(json.dumps(jdata)))
    r = ditto.put(url="https://ditto.eclipse.org/api/2/things/{}".format(thingId), data=json.dumps(jdata))
    logging.debug(r)
    logging.debug(r.text)

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

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
r = ditto.put(url="https://ditto.eclipse.org/api/2/policies/{}".format(policyId), data=json.dumps(jpolicy))
if r.ok:
    logging.info("policy check - OK")
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
else:
    logging.error("Unable to connect to eclipse ditto. Exiting")