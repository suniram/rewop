#! /usr/bin/python
import logging

import hid

from settings import logger_conf, rewop_config


class USBConnector(object):

    def __init__(self, vendor_id, product_id):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = hid.device()
        self.log = logging.getLogger("USBConnector")
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        self.log.debug("Opening usb device vendor id '{}', product_id '{}'".format(self.vendor_id, self.product_id))
        try:
            if not rewop_config['test']:
                self.device.open(self.vendor_id, self.product_id)
        except Exception as exception:
            raise Exception("Error opening usb device vendor id '{}', "
                            "product_id '{}', error '{}'".format(self.vendor_id,
                                                                 self.product_id,
                                                                 exception))
        self.log.debug('USB device opened!')
        return self

    def __exit__(self, *args):
        self.log.debug("Closing usb device vendor id '{}', product_id '{}'".format(self.vendor_id, self.product_id))
        if not rewop_config['test']:
            self.device.close()
        self.log.debug('USB device closed!')
        return self

    def write(self, data: bytes):
        self.log.debug("writing usb data {}".format(data))
        if not rewop_config['test']:
            self.device.write(data)

    def read(self, size):
        self.log.debug("reading usb data")
        data = []

        while True:
            data.extend(self.device.read(size))
            if not data or 13 in data or len(data) >= size:
                break

        b = bytes(data)
        self.log.debug("usb data {}".format(b))
        return b
