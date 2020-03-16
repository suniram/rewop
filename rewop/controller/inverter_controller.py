#! /usr/bin/python
import datetime
import logging
from urllib import request

from rewop.collector.axpertcollector import AxpertCollector, Status
from settings import logger_conf, inverter_conf


def is_load_shedding_time():
    if InverterController.load_shedding_time is None:
        return True

    hours = (datetime.datetime.now() - InverterController.load_shedding_time).total_seconds() / 60.0 / 60.0
    return hours > 4


class InverterController(object):
    load_shedding_time = None
    is_load_shedding = None
    is_uti_mode = None

    def __init__(self):
        self.log = logging.getLogger('InverterController')
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self

    def process_load_shedding(self):
        try:
            is_load_shedding = self.get_load_shedding_status()

            if is_load_shedding is None:
                return None

            if is_load_shedding:
                self.switch_to_load_shedding_on()
            else:
                self.switch_to_load_shedding_off()

            return InverterController.is_load_shedding

        except Exception as e:
            self.log.error("Unable to update load shedding status {}".format(e))
            return None

    def get_load_shedding_status(self):
        try:
            url = 'http://loadshedding.eskom.co.za/LoadShedding/GetStatus'
            status = request.urlopen(url, timeout=10).read()
            self.log.debug("Load Shedding status {}".format(status))
            return status != b'1'
        except Exception as e:
            self.log.error("Unable to determine load shedding status {}".format(e))
        return None

    def switch_to_load_shedding_on(self):

        self.log.debug("Load Shedding!!!")
        if is_load_shedding_time() and not InverterController.is_load_shedding:
            self.log.info("Enable load shedding mode")
            with AxpertCollector() as inverter:
                if inverter.send_command_muchgc('020') == Status.OK:
                    InverterController.is_load_shedding = True
                    InverterController.load_shedding_time = datetime.datetime.now()
                    self.log.info("Load shedding mode enabled")

        if datetime.datetime.now().hour >= inverter_conf['load_shedding_to_utility_start'] or \
                datetime.datetime.now().hour < inverter_conf['load_shedding_to_utility_end']:
            if InverterController.is_uti_mode is None or not InverterController.is_uti_mode:
                with AxpertCollector() as inverter:
                    self.log.info("Switching to Utility")
                    inverter.send_command_pop_utility()
                    InverterController.is_uti_mode = True
                    self.log.info("Load shedding Utility mode enabled")

        else:
            self.log.info(InverterController.is_uti_mode)
            if InverterController.is_uti_mode is None or InverterController.is_uti_mode:
                with AxpertCollector() as inverter:
                    self.log.info("Switching to SBU")
                    inverter.send_command_pop_sbu()
                    InverterController.is_uti_mode = False
                    self.log.info("Load shedding Solar mode enabled")

    def switch_to_load_shedding_off(self):
        self.log.debug("Not Load Shedding")
        if is_load_shedding_time() and InverterController.is_load_shedding:
            self.log.info("Disable load shedding mode")
            with AxpertCollector() as inverter:
                if inverter.send_command_pop_sbu() == Status.OK and inverter.send_command_muchgc('002') == Status.OK:
                    InverterController.is_load_shedding = False
                    InverterController.load_shedding_time = datetime.datetime.now()
                    InverterController.is_uti_mode = False
                    self.log.info("Load shedding mode disabled")
