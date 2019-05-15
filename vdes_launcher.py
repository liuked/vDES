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
# dittourl="http://ditto.eclipse.org"
dittourl="http://10.100.1.123:8080"
# usr = "demo1"
# psw = "demo"
usr = "ditto"
psw = "ditto"

if __name__ == "__main__":

    vdes = vDES(dittourl, usr, psw )

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
