#! /usr/bin/python
import logging
import urllib
from http import client

from settings import logger_conf, econcms_conf, rewop_config


class Emoncms(object):

    def __init__(self):
        self.log = logging.getLogger('Emoncms')
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        self.connection = client.HTTPSConnection(econcms_conf['server'])
        return self

    def __exit__(self, *args):
        self.connection.close()
        return self

    def send(self, node, json_data):

        try:
            url = "/input/post?node={}&fulljson={}&apikey={}".format(node, urllib.parse.quote_plus(json_data),
                                                                     econcms_conf['api_key'])

            if rewop_config['test']:
                return True

            self.connection.request("GET", url)
            response = self.connection.getresponse()

            if response.status == 200:
                return True
            else:
                self.log.error("Emoncms http request declined with status {} and reason {} ".format(response.status,
                                                                                                    response.reason))
        except Exception as e:
            self.log("Error sending data to emoncms, node '{}' data '{}' , exception '{}'".format(node, json_data, e))

        return False
