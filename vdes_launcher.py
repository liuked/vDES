import logging
logging.basicConfig(level=logging.DEBUG)
import sys, os
sys.path.append(os.path.abspath(os.path.join("..")))
from vSON_southbound import vson
from vSON_northbound import RESTfulAPI
import threading
import argparse
from vSON_graph import topo


### set log destination
# logging.basicConfig(filename="vSON.log", level=logging.DEBUG)


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", dest="port_num", help="select on wich port to open the listener, default = 2904",
                  metavar="<port>", type=int, default=5050)
parser.add_argument("--api_port", type=int, help="port for restful API server", default=5051)
args = parser.parse_args()


if __name__ == "__main__":

    # logging.info("Starting Southbound listener deamon...")
    # t = threading.Thread(target=ES('', port_num).listen, de)
    # t.setDaemon(True)
    # t.start()
    #
    # logging.info("Starting Device Monitor deamon...")
    # topo.start_device_monitor()
    #
    #
    # logging.info("Starting Nortbound Rest Interface...")
    # RESTfulAPI(args.api_port)
