import logging
logging.basicConfig(level=logging.DEBUG)
import sys, os
from vdes_core import vDES
sys.path.append(os.path.abspath(os.path.join("..")))
import vdes_northbound

import threading
import argparse


## set log destination
logging.basicConfig(level=logging.DEBUG)
rest_port = 1234
# dittourl="http://localhost:8080"
dittourl="http://ditto.eclipse.org"


if __name__ == "__main__":

    vdes = vDES(dittourl, "demo1", "demo")

    threading.Thread(target=vdes_northbound.runrest, args=(rest_port, vdes)).start()

    vdes.foreverloop()
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
