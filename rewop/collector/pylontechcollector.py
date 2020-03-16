#! /usr/bin/python
import json
import logging
import os
from collections import namedtuple

from rewop.communication.connector_serial import SerialConnector
from rewop.http.emoncms import Emoncms
from settings import logger_conf, pylontech_conf, rewop_config

PowerSystemFields = [b'System Volt', b'System Curr', b'System SOC', b'System SOH', b'Highest voltage',
                     b'Average voltage', b'Lowest voltage']

PowerSystemResponse = namedtuple('Response', ['system_volts', 'system_current', 'system_soc', 'system_soh', 'volts_max',
                                              'volts_avg', 'volts_min'])

SOHResponse = namedtuple('Response', ['battery', 'cell', 'volts', 'count', 'status'])


class PylontechCollector(object):
    error_count = 0

    def __init__(self, port):
        self.log = logging.getLogger('Pylontech')
        self.log.setLevel(logger_conf['level'])
        self.port = port
        self.baud = pylontech_conf['baud']

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self

    def process(self):
        try:
            response = self.process_power_system()
        except Exception as e:
            self.log.error("Pylontech processing error {}".format(e))

        if not response:
            PylontechCollector.error_count += 1
        else:
            PylontechCollector.error_count = 0

        if PylontechCollector.error_count > pylontech_conf['error_reboot_count']:
            self.log.error(
                "Pylontech Controller maximum errors reached {}, rebooting the system".format(
                    PylontechCollector.error_count))
            os.system('reboot')

        return response

    def process_power_system(self):
        response = self.send_pwrsys_command()

        if response:
            self.log.info("Pylontech Data {}".format(response))

            try:
                with Emoncms() as emoncms:
                    emoncms.send(pylontech_conf['emoncms_node'], json.dumps(response._asdict()))
            except Exception as e:
                self.log.error("Error connecting to emoncms {}".format(e))

        return response

    def process_soh(self, database, battery, date_time):
        soh_responses = self.send_soh_command(battery)

        if soh_responses:
            self.log.info("Pylontech soh {}".format(soh_responses))

            for soh in soh_responses:
                json_response = json.loads(json.dumps(soh._asdict()))
                database.insert_battery_soh(date_time, json_response)

    def send_pwrsys_command(self):

        if not rewop_config['test']:
            data = self.send_command('pwrsys')
        else:
            data = b'pwrsys\n\r@\r\r\n Power System Information\r\r\n ---------------------------------\r\r\n System is discharging\r\r\n Total Num                : 2        \r\r\n Present Num              : 2        \r\r\n Sleep Num                : 0        \r\r\n System Volt              : 52566    mV\r\r\n System Curr              : -3448    mA\r\r\n System RC                : 99876    mAH\r\r\n System FCC               : 99900    mAH\r\r\n System SOC               : 99       %\r\r\n System SOH               : 100      %\r\r\n Highest voltage          : 3521     mV\r\r\n Average voltage          : 3504     mV\r\r\n Lowest voltage           : 3486     mV\r\r\n Highest temperature      : 29000    mC\r\r\n Average temperature      : 28500    mC\r\r\n Lowest temperature       : 28000    mC\r\r\n Recommend chg voltage    : 53250    mV\r\r\n Recommend dsg voltage    : 47000    mV\r\r\n Recommend chg current    : 10000    mA\r\r\n Recommend dsg current    : -50000   mA\r\n\rCommand completed successfully\r\n\r$$\r\n\rpylon_debug>'

        if not data:
            return

        fields = data.split(b'\n')

        response = PowerSystemResponse(
            *list(map(lambda f: (f.rstrip(b'\r').split(b':')[1].lstrip().split(b' ')[0]).decode(),
                      self.filter(fields, PowerSystemFields))))

        return response

    def send_soh_command(self, battery):

        if not rewop_config['test']:
            if battery == 0:
                cmd = 'soh'
            else:
                cmd = 'soh {}'.format(battery)
            data = self.send_command(cmd)
        else:
            data = b'soh\n\r@\r\r\nPower   1\r\r\nBattery    Voltage    SOHCount   SOHStatus \r\r\n0          3234       0          Normal    \r\r\n1          3235       0          Normal    \r\r\n2          3233       0          Normal    \r\r\n3          3233       0          Normal    \r\r\n4          3236       0          Normal    \r\r\n5          3235       0          Normal    \r\r\n6          3236       0          Normal    \r\r\n7          3235       0          Normal    \r\r\n8          3235       0          Normal    \r\r\n9          3236       0          Normal    \r\r\n10         3235       0          Normal    \r\r\n11         3238       0          Normal    \r\r\n12         3235       0          Normal    \r\r\n13         3235       0          Normal    \r\r\n14         3234       0          Normal    \r\n\rCommand completed successfully\r\n\r$$\r\n\rpylon_debug>'

        if not data:
            return

        fields = data.split(b'\n')

        fields = fields[4:19]
        return list(map(lambda f: SOHResponse(*('{} ' + (f.rstrip(b'\r').lstrip()).decode())
                                              .format(battery).split()), fields))

    @staticmethod
    def filter(string, substr):
        return [str for str in string if
                any(sub in str for sub in substr)]

    def send_command(self, cmd):
        with SerialConnector(self.port, self.baud) as connector:
            try:
                connector.write("{}\r".format(cmd).encode())
                data = connector.read(2048)
                self.log.debug("Pylontech {} Response {}".format(cmd, data))
                return data
            except Exception as e:
                self.log.error("Error sending command {} to the Pylontech battery, the error is {}".format(cmd, e))
