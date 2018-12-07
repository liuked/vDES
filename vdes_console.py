import cmd, sys
from vdes_southbound import *

class vdesShell(cmd.Cmd):
    intro = 'Welcome to vDES shell.   Type help or ? to list commands.\n'
    prompt = '(vdes) '
    file = None

    # ----- basic turtle commands -----
    def do_charge(self, arg):
        'Order the ESP to charge'
        vdes1.esp_charge(*parse(arg))

    def do_unplug(self, arg):
        'Order the ESP to unplug'
        vdes1.esp_charge(*parse(arg))

    def do_serve(self, arg):
        'Order the ESP to ser ve the grid'
        vdes1.esp_charge(*parse(arg))


def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return tuple(map(int, arg.split()))

