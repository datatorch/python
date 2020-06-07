import sys
import time
import threading

done = False
text = ""


class Spinner(object):
    """ Creates a spinning icon in CLI, useful for indicating progress """

    def __init__(self, string: str = "Loading"):
        global done, text
        done = False
        text = string
        self.text = text
        self._thread = threading.Thread(target=self._draw_spinner)
        self._thread.start()

    def _draw_spinner(self, speed=0.1):
        global done, text
        while True:
            for cursor in "|/-\\":
                sys.stdout.write("{} {} ".format(cursor, text))
                sys.stdout.flush()
                time.sleep(speed)
                sys.stdout.write("\r")
                sys.stdout.write("\b")
                if done:
                    return

    def set_text(self, string: str):
        global text
        text = string

    def done(self, text: str = None):
        global done
        done = True
        self._thread.join()

        if text:
            print(f'{text} {" " * (len(self.text) + 2)}')
