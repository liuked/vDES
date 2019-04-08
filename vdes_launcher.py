import logging
logging.basicConfig(level=logging.DEBUG)
import sys, os
from vdes_core import vDES
sys.path.append(os.path.abspath(os.path.join("..")))

import threading
import argparse


## set log destination
logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":

    vdes = vDES("https://ditto.eclipse.org/api/2/things/", "demo1", "demo")

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
