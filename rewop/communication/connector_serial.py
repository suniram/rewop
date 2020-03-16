#! /usr/bin/python
import logging

from serial import (Serial)

from settings import logger_conf, rewop_config


class SerialConnector(object):

    def __init__(self, port, baud):
        self.port = port
        self.log = logging.getLogger("SerialConnector")
        self.log.setLevel(logger_conf['level'])
        self.baud = baud

    def __enter__(self):
        self.log.debug("Opening serial port '{}'".format(self.port))
        try:
            if not rewop_config['test']:
                self.device = Serial(self.port, self.baud, timeout=1)
        except Exception as exception:
            raise Exception("Error opening serial port '{}', "
                            " error '{}'".format(self.port,
                                                 exception))
        self.log.debug('Serial port opened!')
        return self

    def __exit__(self, *args):
        self.log.debug("Closing serial port '{}'".format(self.port))
        if not rewop_config['test']:
            self.device.close()
        self.log.debug('Serial port closed!')
        return self

    def write(self, data: bytes):
        self.log.debug("writing serial port data {}".format(data))
        if not rewop_config['test']:
            self.device.write(data)
            self.device.flush()

    def read(self, size):
        self.log.debug("reading serial port")

        if not rewop_config['test']:
            try:
                data = self.device.read(size)
            except Exception as e:
                print(e)
        else:
            data = []

        self.log.debug("serial port data {}".format(data))
        b = bytes(data)
        self.log.debug("serial port bytes {}".format(b))
        return b
