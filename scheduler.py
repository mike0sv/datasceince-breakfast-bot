import datetime
import time
import sys
from threading import Thread


class Event:
    def __init__(self, cron_provider, callback, timeout=5):
        self.cron = cron_provider
        self.callback = callback
        self.timeout = timeout
        self.last = None

    def _check(self, pair):
        cron, now = pair
        return cron == '*' or int(cron) == now

    def _run(self):
        while True:
            cron = self.cron().split()
            date = datetime.datetime.now()
            now = (date.minute, date.hour, date.day, date.month, date.weekday())
            if not self.last or self.last != now:
                if all(map(self._check, zip(cron, now))):
                    self.last = now
                    try:
                        self.callback()
                    except:
                        print(sys.exc_info())

            time.sleep(self.timeout)

    def run(self, daemon=False):
        if daemon:
            t = Thread(target=self._run)
            t.daemon = True
            t.start()
        else:
            self._run()


def main():
    c = '* 13 * * *'

    def cb():
        print(time.time())

    e = Event(lambda: c, cb, )
    e._run()


if __name__ == '__main__':
    main()
