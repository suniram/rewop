#! /usr/bin/python
#
import datetime
import logging
import signal
import time
from dataclasses import dataclass

from dataclasses_json import dataclass_json

from rewop.collector.axpertcollector import AxpertCollector, AxpertResponse
from rewop.collector.pylontechcollector import PylontechCollector, PowerSystemResponse
from rewop.controller.inverter_controller import InverterController
from rewop.controller.poolcontroller import PoolController
from rewop.http.emoncms import Emoncms
from settings import logger_conf, rewop_config


@dataclass_json
@dataclass
class SystemData:
    grid_available: int = 0
    grid_mode: int = 0
    battery_mode: int = 0
    fault_mode: int = 0
    solar_mode: int = 0
    pool_mode: int = 0
    pool_on: int = 0
    grid_watts: int = 0
    pv_watts: int = 0
    battery_watts: int = 0
    inverter_watts: int = 0
    battery_soc: int = 0
    battery_volts: float = 0
    inverter_load: int = 0
    load_shedding: int = 0


def process_pylontech(port):
    with PylontechCollector(port) as collector:
        return collector.process()


def process_axpert(port):
    AxpertCollector.port = port
    with AxpertCollector() as collector:
        return collector.process()


class Collector(object):
    CHARGE_PV = '110'
    CHARGE_AC = '101'
    CHARGE_PV_AC = '111'

    def __init__(self):
        self.is_pool_pump_on = None
        self.is_load_shedding = 0
        self.pool_pump_time = datetime.datetime.now()
        self.log = logging.getLogger('Axpert')
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self

    def is_pylontech_port(self, port):
        for x in range(3):
            try:
                p_response = process_pylontech(port)

                if p_response:
                    return True
            except Exception as e:
                self.log("Pylontech server error {}".format(e))
            time.sleep(2)
        return False

    def process(self):
        self.log.info("Starting collectors")

        signal.signal(signal.SIGALRM, self.handler)

        pylontech_port = '/dev/ttyUSB0'
        axpert_port = '/dev/ttyUSB1'

        if not self.is_pylontech_port(pylontech_port):
            # switch the ports
            pylontech_port = '/dev/ttyUSB1'
            axpert_port = '/dev/ttyUSB0'

        while True:
            # 30 second timeout
            signal.alarm(120)

            try:
                p_response = process_pylontech(pylontech_port)
            except Exception as e:
                self.log("Pylontech server error {}".format(e))

            try:
                a_response = process_axpert(axpert_port)
            except Exception as e:
                self.log("Axpert server error {}".format(e))

            system_data = self.get_system_data(p_response, a_response)

            if system_data:
                try:
                    with PoolController(system_data) as pool_controller:
                        system_data.pool_mode = pool_controller.process()
                        if system_data.pool_mode == PoolController.ON:
                            system_data.pool_on = 1
                        else:
                            system_data.pool_on = 0
                except Exception as e:
                    self.log.error("Error processing pool data {}".format(e))

                with InverterController() as load_shedding_controller:
                    is_load_shedding = load_shedding_controller.process_load_shedding()

                    if is_load_shedding is None:
                        system_data.load_shedding = 2
                    elif is_load_shedding:
                        system_data.load_shedding = 0
                    else:
                        system_data.load_shedding = 1

                self.log.info("System Data {}".format(system_data))
                try:
                    with Emoncms() as emoncms:
                        emoncms.send('system', system_data.to_json())
                except Exception as e:
                    self.log.error("Error connecting to emoncms {}".format(e))

            # remove the timeout
            signal.alarm(0)
            time.sleep(rewop_config['interval'])

    def get_system_data(self, p_response: PowerSystemResponse, a_response: AxpertResponse):
        system_data = SystemData()

        if p_response and a_response:
            if float(a_response.grid_voltage_1) > 0:
                system_data.grid_available = 1

            if a_response.work_mode_2 == 'L':
                system_data.grid_mode = 1
            elif a_response.work_mode_2 == 'B':
                system_data.battery_mode = 1

            if a_response.fault_code_2 == '00':
                system_data.fault_mode = 1

            if system_data.grid_mode == 1:
                system_data.grid_watts = int(a_response.ac_output_watt_1)

            system_data.inverter_load = int(a_response.inverter_load_2)

            system_data.pv_watts = int(a_response.pv_charging_watt_1)

            system_data.inverter_watts = int(a_response.ac_output_watt_1)

            sc = int(p_response.system_current) / 1000
            system_data.battery_volts = int(p_response.system_volts) / 1000
            system_data.battery_watts = sc * system_data.battery_volts
            system_data.battery_soc = int(p_response.system_soc)
            system_data.pool_mode = PoolController.UNKNOWN

            charge_status = a_response.device_status_1[-3:]

            if charge_status == Collector.CHARGE_PV or charge_status == Collector.CHARGE_PV_AC:
                system_data.solar_mode = 1

            if charge_status == Collector.CHARGE_AC:
                system_data.grid_watts += system_data.battery_watts

            if charge_status == Collector.CHARGE_PV_AC:
                system_data.grid_watts += (int( a_response.total_charging_apms_2) -
                                           int(a_response.pv_input_amps_for_battery_2)) * \
                                          float(a_response.battery_voltage_1)

            return system_data
        else:
            self.log.info("Missing response data, pylontech {}, axpert {}".format(p_response, a_response))

    def handler(self, signum, frame):
        self.log.error("Process timeout {}, frame {}".format(signum, frame))
        raise Exception("Process timeout")
