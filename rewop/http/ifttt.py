#! /usr/bin/python
import logging
from http import client

from settings import logger_conf, rewop_config, ifttt_conf


class Ifttt(object):

    def __init__(self):
        self.log = logging.getLogger('IFTTT')
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        self.connection = client.HTTPSConnection(ifttt_conf['server'])
        return self

    def __exit__(self, *args):
        self.connection.close()
        return self

    def send_trigger(self, trigger):

        self.log.info("IFTTT trigger {}".format(trigger))
        try:
            url = "/trigger/{}/with/key/{}".format(trigger, ifttt_conf['api_key'])

            if rewop_config['test']:
                return True

            self.connection.request("POST", url)
            response = self.connection.getresponse()

            if response.status == 200:
                return True
            else:
                self.log.error("IFTTT http request declined with status {} and reason {} ".format(response.status,
                                                                                                    response.reason))
        except Exception as e:
            self.log("Error sending data to IFTTT, trigger '{}', exception {}".format(trigger, e))

        return False
