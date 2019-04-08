import paho.mqtt.client as mqtt
import threading
import logging
import argparse
import json
from datetime import datetime

class Data:
    value = 0

    def increase():
        Data.value = Data.value +1

    def decrease():
        Data.value = Data.value -1


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global sub_topic_lst
    global ready
    logging.debug("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    logging.debug("topics{}".format(sub_topic_lst))
    for t in sub_topic_lst:
        client.subscribe(t,1)
        logging.debug("subscribed to {}".format(t))
    ready = True


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global stopf
    logging.info("rcvd: "+msg.topic+" "+str(msg.payload))
    if msg.payload == "stop":
        stopf = True


def on_publish(client, userdata, mid):
    logging.debug("published: {:d})".format(mid))


def on_disconnect(client, userdata, rc):
    logging.warning("{} nor implemented".fromat(__name__))


def get_dev_data():
    global id
    global devtype
    Data.increase()
    jdata = {
        "devID": "{:04x}".format(id),
        "attributes": {
            "devtype": devtype
        },
        "features": {
            "testdata": {
                "properties": {
                    "status": {
                        "value": Data.value,
                        "lastMeasured": datetime.utcnow().strftime("%y-%m-%dT%H:%M"),
                        "units": "u"
                    }
                }
            },
        },
    }
    return jdata


def mqtt_netloop(client):
    logging.debug("connecting client")
    client.loop_forever()


def eventloop(client):
    global stopf

    while(stopf==False):
        jdata = get_dev_data()  # blocking
        logging.info("recorded: {}".format(jdata))
        msginfo = client.publish(pub_topic, json.dumps(jdata), 1)
        logging.debug("publishing: {:d}".format(msginfo.mid))
        #time.sleep(1)
        input()


logging.basicConfig(level=logging.INFO)
pub_topic = "vmcm"
devtype = "battery"
stopf = False

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", dest="broker_port", help="broker port", metavar="<port>", type=int, default=1883)
parser.add_argument("-H", "--host", dest="broker_host", help="broker host IP", type=str,  metavar="<port>", default="localhost")
parser.add_argument("-t", "--tipiclst", dest="topiclst", help="subscription topics", type=str, nargs="*",  metavar="<topic1> <topic2> ...", default=["vdes"])
parser.add_argument("-i", "--id", dest="id", help="client id", metavar="<id>", type=int, default=0)
args = parser.parse_args()

id = args.id
sub_topic_lst = args.topiclst  # ["vdes", "$SYS/#"] for debug
broker_port = args.broker_port
broker_host = args.broker_host

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.connect(broker_host, broker_port, 60)

# start mqtt client
ready = False
logging.info("starting mqtt client id: {:04X}".format(id))
threading.Thread(target=mqtt_netloop, args={client}).start()

# start data listener (only when connected)
while not ready:
    pass
logging.info("starting loop")
eventloop(client)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.