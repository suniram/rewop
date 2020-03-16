#! /usr/bin/python
import datetime
import logging

from rewop.http.ifttt import Ifttt
from settings import logger_conf, pool_pump_conf


class PoolController(object):
    is_on = None
    time_last_changed = None
    pv_low_time = None
    mode = 0

    UNKNOWN = 0
    OFF_START_UP = 1
    OFF_GRID_MODE = 2
    OFF_HIGH_LOAD = 3
    OFF_LOW_SOC = 4
    OFF_LOW_PV = 5

    ON = 10

    def __init__(self, system_data):
        self.system_data = system_data
        self.log = logging.getLogger('PoolController')
        self.log.setLevel(logger_conf['level'])

    def __enter__(self):
        if PoolController.is_on is None:
            self.pool_off(PoolController.OFF_START_UP)
        return self

    def __exit__(self, *args):
        return self

    def process(self):
        pv_extra_power = self.system_data.pv_watts - self.system_data.inverter_watts

        is_pv_low = pv_extra_power < pool_pump_conf['pv_low']
        is_pv_high = pv_extra_power > pool_pump_conf['pv_high']

        if not is_pv_low:
            # reset the pv low time
            PoolController.pv_low_time = None

        if PoolController.is_on:
            # switch off if system is in grid mode
            if self.system_data.grid_mode == 1:
                self.pool_off(PoolController.OFF_GRID_MODE)
                PoolController.pv_low_time = None
            # switch off if the load on the inverter is high
            elif self.system_data.inverter_watts > pool_pump_conf['load_high']:
                self.pool_off(PoolController.OFF_HIGH_LOAD)
                PoolController.pv_low_time = None
            # switch off if the soc is low
            elif self.system_data.battery_soc < pool_pump_conf['soc_low']:
                self.pool_off(PoolController.OFF_LOW_SOC)
                PoolController.pv_low_time = None
            # switch off if the pv power is low
            elif is_pv_low:
                # we don't want to switch of for every cloud, let give it a delay before switching off
                if PoolController.pv_low_time is None:
                    PoolController.pv_low_time = datetime.datetime.now()
                    self.log.info("Entering pv low sate")
                else:
                    pv_low_time = (datetime.datetime.now() - PoolController.pv_low_time).total_seconds() / 60.0
                    if pv_low_time > pool_pump_conf['pv_low_delay']:
                        self.pool_off(PoolController.OFF_LOW_PV)
                        PoolController.pv_low_time = datetime.datetime.now()
        else:
            time_laps = (datetime.datetime.now() - PoolController.time_last_changed).total_seconds() / 60.0

            # wait 10 mins (on_delay_period) before allowing the on switch, the on switch will not happen until
            # on_delay_period of time after the previous off switch.

            delay = pool_pump_conf['on_delay']

            if PoolController.pv_low_time is not None:
                delay = delay * 2

            if time_laps > delay:
                # only switch on if the system is on battery mode
                if self.system_data.battery_mode == 1:
                    # switch on if the soc is low and pv is high,
                    # there is enough power to support ac output, the pump and to charge the battery
                    if self.system_data.battery_soc > pool_pump_conf['soc_low'] and is_pv_high:
                        self.pool_on(PoolController.ON)
                    # if the soc is full, the pv will stay low, it only draws enough power to support the ac output.
                    # We can switch on if the soc is high and pv low.
                    elif self.system_data.battery_soc > pool_pump_conf['soc_high'] and not is_pv_low:
                        self.log.info("Pool pv low sate ON")
                        self.pool_on(PoolController.ON)
        return PoolController.mode

    def pool_on(self, pool_mode):
        self.log.info("Pool On {}".format(pool_mode))
        try:
            with Ifttt() as ifttt:
                try:
                    PoolController.is_on = ifttt.send_trigger(pool_pump_conf['on_trigger'])
                    PoolController.time_last_changed = datetime.datetime.now()
                    PoolController.mode = pool_mode
                    return
                except Exception as e:
                    self.log.error("Error processing pool on trigger {}".format(e))
        except Exception as e:
            self.log.error("Error processing pool on trigger {}".format(e))
        PoolController.mode = PoolController.UNKNOWN

    def pool_off(self, pool_mode):
        self.log.info("Pool Off {}".format(pool_mode))
        try:
            with Ifttt() as ifttt:
                PoolController.is_on = not ifttt.send_trigger(pool_pump_conf['off_trigger'])
                PoolController.time_last_changed = datetime.datetime.now()
                PoolController.mode = pool_mode
                return
        except Exception as e:
            self.log.error("Error processing pool off trigger {}".format(e))
        PoolController.mode = PoolController.UNKNOWN
