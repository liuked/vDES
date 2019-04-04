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
    print(msg.payload)
    logging.debug("rcvd: "+msg.topic+" "+str(msg.payload))
    jdata = {
        "attributes": {
        }
    }
    jdata["attributes"]=json.loads(msg.payload.decode("utf-8"))
    logging.debug(json.dumps(jdata))
    r = ditto.post(url="https://ditto.eclipse.org/api/2/things", data=json.dumps(jdata) )
    logging.info(r.status_code+" "+r.reason)
    if r.ok:
        logging.debug(r.json)

logging.basicConfig(level=logging.DEBUG)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

# open req session to eclipse ditto
ditto = requests.Session()
ditto.auth=requests.auth.HTTPBasicAuth("demo1", "demo")
r = ditto.get(url="https://ditto.eclipse.org/api/2/things/%3Aff69e424-aff1-47dd-9f4b-bfc142ff7927")
logging.debug(r.text)
if r.status_code == 200:
    logging.info("connected successfully")
# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()