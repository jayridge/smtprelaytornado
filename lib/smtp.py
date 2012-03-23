from tornado import ioloop, httpclient
from tornadomail.message import EmailMessage, EmailMultiAlternatives
from tornadomail.backends.smtp import EmailBackend
import settings
import logging
import urllib
import time
import math
import functools
from collections import deque

class smtprelay:
    def __init__(self, host, port=25, user=None, password=None, usetls=False, loop=None):
        self.ioloop = loop or ioloop.IOLoop.instance()
        self.write_queue = deque()
        self.started = time.time()
        self.error_level = 0
        self.stats = { 
            'sends':0,
            'failures':0,
            'successes':0,
        }
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.usetls = usetls
        self.connection = EmailBackend(host, port, user, password, usetls)
        self.sweeper = ioloop.PeriodicCallback(self.run_sweeper, 1000*1, self.ioloop)
        self.sweeper.start()

    def run_sweeper(self):
        if not self.error_level:
            while len(self.write_queue):
                self.send(self.write_queue.popleft())
        else:
            self.error_level -= 1

    def get_stats(self):
        stats = self.stats.copy()
        stats['queue_len'] = len(self.write_queue)
        stats['error_level'] = self.error_level
        stats['uptime'] = time.time() - self.started
        return stats

    def send(self, msg):
        if self.error_level:
            self.write_queue.append(msg)
        else:
            self.stats['sends'] += 1
            msg.send(callback=functools.partial(self._finish_send, msg=msg))

    def _finish_send(self, num, msg):
        self.stats['successes'] += num
        if not num:
            self.stats['failures'] += 1
            self.error_level += (1 + self.error_level/2)

