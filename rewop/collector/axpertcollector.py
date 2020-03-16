#! /usr/bin/python
import datetime
import json
import logging
import os
import time
from collections import namedtuple
from enum import IntEnum
from struct import pack

from crc16 import crc16xmodem

from rewop.communication.connector_serial import SerialConnector
from rewop.http.emoncms import Emoncms
from settings import axpert_conf, logger_conf, rewop_config

NAK, ACK = b'NAK', b'ACK'

Response = namedtuple('Response', ['status', 'data'])
AxpertResponse = namedtuple('data', ['grid_voltage_1', 'grid_frequency_1', 'ac_output_voltage_1',
                                     'ac_output_frequency_1', 'ac_output_va_1', 'ac_output_watt_1',
                                     'output_load_percentage_1', 'bus_voltage_1', 'battery_voltage_1',
                                     'battery_charge_amps_1', 'battery_capacity_1', 'inverter_heat_sink_temp_1',
                                     'pv_input_amps_1', 'pv_input_voltage_1', 'battery_voltage_scc_1',
                                     'battery_discharge_amps_1', 'device_status_1',
                                     'battery_voltage_offset_for_fan_1', 'eeprom_version_1',
                                     'pv_charging_watt_1', 'mask_1', 'parallel_num_2', 'serial_number_2',
                                     'work_mode_2', 'fault_code_2', 'grid_voltage_2', 'grid_frequency_2',
                                     'ac_output_voltage_2', 'ac_output_frequency_2', 'ac_output_va_2',
                                     'ac_output_watt_2', 'inverter_load_2', 'battery_voltage_2',
                                     'battery_charge_amps_2', 'battery_capacity_2', 'pv_input_voltage_2',
                                     'total_charging_apms_2', 'total_ac_output_va_2', 'total_output_watt_2',
                                     'total_ac_output_percentage_2', 'inverter_status_2', 'output_mode_2',
                                     'charge_source_priority_2', 'max_charge_amps_2', 'max_charge_range_2',
                                     'max_ac_charge_amps_2', 'pv_input_amps_for_battery_2',
                                     'battery_discharge_amps_2'])


class Status(IntEnum):
    OK = 1
    KO = 2
    CRC = 3
    ERROR = 4


class AxpertCollector(object):
    error_count = 0
    port = None

    def __init__(self):
        self.log = logging.getLogger('Axpert')
        self.log.setLevel(logger_conf['level'])
        self.baud = axpert_conf['baud']

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self

    def process(self):
        try:
            response = self.process_axpert_data()
        except Exception as e:
            self.log.error("Axpert processing error {}".format(e))

        if not response:
            AxpertCollector.error_count += 1
        else:
            AxpertCollector.error_count = 0

        if AxpertCollector.error_count > axpert_conf['error_reboot_count']:
            self.log.error(
                "Axpert Controller maximum errors reached {}, rebooting the system".format(AxpertCollector.error_count))
            os.system('reboot')

        return response

    def process_axpert_data(self):
        qpigs_response = self.send_command_qpigs()
        time.sleep(1)
        qpgs0_response = self.send_command_qpgs0()

        if qpigs_response and qpgs0_response:
            response = AxpertResponse(*qpigs_response, *qpgs0_response)

            self.log.info("Axpert Data {}".format(response))

            try:
                with Emoncms() as emonscms:
                    emonscms.send(axpert_conf['emoncms_node'], json.dumps(response._asdict()))
            except Exception as e:
                self.log.error("Error connecting to emoncms {}".format(e))

            return response

    # Device data enquiry
    def send_command_qpigs(self):

        if not rewop_config['test']:
            response = self.send_inverter_command('QPIGS', '')
        else:
            response = Response(Status.OK, '238.6 49.9 230.2 49.8 0736 0691 017 385 48.60 000 023 '
                                           '0058 0000 000.0 00.00 00016 01010000 00 00 03000 010')
        if response.status != Status.OK:
            return
        return response.data.split(' ')

    # Device extra data enquiry
    def send_command_qpgs0(self):

        if not rewop_config['test']:
            response = self.send_inverter_command('QPGS0', '')
        else:
            response = Response(Status.OK, '1 92931504140321 B 00 237.0 50.15 230.1 50.17 0621 0565 014 49.6 000 043'
                                           ' 113.2 000 00621 00565 014 10100011 0 3 040 140 02 05 008')
        if response.status != Status.OK:
            return
        return response.data.split(' ')

    # Device settings enquiry
    def send_command_qpiri(self):

        if not rewop_config['test']:
            response = self.send_inverter_command('QPIRI', '')
        else:
            response = Response(Status.OK, '230.0 21.7 230.0 50.0 21.7 5000 4000 48.0 48.0 48.0 52.4 52.0 2 02 040 1 2 '
                                           '1 9 01 0 0 51.0 0 1 000')
        if response.status != Status.OK:
            return
        return response.data.split(' ')

    # Back To Utility volts
    def send_command_pbcv(self, volts):

        if not rewop_config['test']:
            response = self.send_inverter_command('PBCV', volts)
        else:
            response = Response(Status.OK, '')
        return response.status

        # Back To Battery volts

    def send_command_pbdv(self, volts):

        if not rewop_config['test']:
            response = self.send_inverter_command('PBDV', volts)
        else:
            response = Response(Status.OK, '')
        return response.status

        # Output source priority

    def send_command_pop(self, pop):
        if not rewop_config['test']:
            response = self.send_inverter_command('POP', pop)
        else:
            response = Response(Status.OK, '')

        time.sleep(30)
        return response.status

    # Output source priority to Utility
    def send_command_pop_utility(self):
        return self.send_command_pop('00')

    # Output source priority to SBU
    def send_command_pop_sbu(self):
        return self.send_command_pop('02')

    def send_command_muchgc(self, amps):
        if not rewop_config['test']:
            response = self.send_inverter_command('MUCHGC', amps)
        else:
            response = Response(Status.OK, '')

        time.sleep(20)

        return response.status

    def send_inverter_command(self, command: str, value: str):

        self.log.debug("Axpert Inverter command '{}' value '{}'".format(command, value))
        command_crc = self.calculate_crc(command, value)
        response = self.send_command(command_crc)
        self.log.debug(
            "{} Axpert Inverter command '{}' value '{}' response '{}'".format(datetime.datetime.now(), command, value,
                                                                              response))

        return response

    def send_inverter_command(self, command: str, value: str):

        self.log.debug("Axpert Inverter command '{}' value '{}'".format(command, value))
        command_crc = self.calculate_crc(command, value)
        response = self.send_command(command_crc)
        self.log.debug(
            "{} Axpert Inverter command '{}' value '{}' response '{}'".format(datetime.datetime.now(), command, value,
                                                                              response))

        return response

    def send_command(self, request: bytes):

        try:
            with SerialConnector(AxpertCollector.port, self.baud) as connector:
                try:
                    # write the first 8 bytes
                    connector.write(request[:8])
                    # if we have more than 8 byte, write the last 8 bytes
                    if len(request) > 8:
                        connector.write(request[8:])

                    time.sleep(1)

                    data_read = connector.read(2000)

                    # remove the padding chars
                    data = data_read.rstrip(b'\x00')

                    # remove the cr
                    data = data.rstrip(b'\r')

                    response = Response(self.parse_response_status(data), data[1:-2].decode())

                    if response.status == Status.CRC:
                        self.log.info("CRC failure {} : {}".format(request, data_read))

                    return response
                except Exception as e:
                    self.log.error("Error sending command '{}' - '{}'".format(request, e))
        except Exception as e:
            self.log.error("Axpert USB error - Error sending command '{}' - '{}'".format(request, e))

        return Response(Status.ERROR, '')

    @staticmethod
    def calculate_crc(cmd: str, value: str):
        encoded_cmd = cmd.encode() + value.encode()
        crc16 = crc16xmodem(encoded_cmd)
        checksum = pack('>H', crc16)

        # need to +1 if the crc is a '\n','\r' or '(', \n = 10, \r = 13, ( = 40
        if checksum[1] == 10 or checksum[1] == 13 or checksum[1] == 40:
            crc16 += 1
            checksum = pack('>H', crc16)

        return encoded_cmd + checksum + b'\r'

    @staticmethod
    def parse_response_status(data):

        if NAK in data:
            return Status.KO

        data_crc = data[-2:]

        calculated_crc = pack('>H', crc16xmodem(data[:-2]))

        # need to +1 if the crc is a '\n','\r' or '(', \n = 10, \r = 13, ( = 40
        if calculated_crc[1] == 10 or calculated_crc[1] == 13 or calculated_crc[1] == 40:
            calculated_crc = pack('>H', crc16xmodem(data[:-2]) + 1)

        if calculated_crc == data_crc:
            return Status.OK
        return Status.CRC
