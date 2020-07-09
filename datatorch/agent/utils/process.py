import os
import sys


def restart():
    """ Restarts the current process running with itself """
    args = sys.argv[:]
    args.insert(0, sys.executable)
    if sys.platform == "win32":
        args = ['"%s"' % arg for arg in args]
    os.execv(sys.executable, args)
