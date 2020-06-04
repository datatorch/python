import sys
import time
import threading

done = False


class Spinner(object):
    def __init__(self, text: str = 'Loading'):
        global done
        done = False
        self.text = text
        self._thread = threading.Thread(target=self._draw_spinner)
        self._thread.start()

    def _draw_spinner(self, speed=0.1):
        global done
        while True:
            for cursor in '|/-\\':
                sys.stdout.write('{} {} '.format(cursor, self.text))
                sys.stdout.flush()
                time.sleep(speed)
                sys.stdout.write('\r')
                sys.stdout.write('\b')
                if done:
                    return

    def done(self, text: str = None):
        global done
        done = True
        self._thread.join()

        if text:
            print('{}'.format(text, ' ' * (len(self.text) + 2)))
