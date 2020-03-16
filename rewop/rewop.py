#! /usr/bin/python
import logging
import os
import sys
import time
from multiprocessing.context import Process

from rewop.collector.collector import Collector
from settings import logger_conf, APP_PATH

curr_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir))

if root_dir not in sys.path:
    sys.path.append(root_dir)


def processor_server_create():
    with Collector() as collector:
        try:
            collector.process()
        except Exception as e:
            print('collector error, restarting.... {}'.format(e))


def processor_start_server():
    print('Starting collector server')
    process = Process(
        target=processor_server_create
    )
    process.start()
    print('Collector server started')
    return process


def main():
    logging.basicConfig(
        format=logger_conf['format'],
        filename='{}/{}'.format(APP_PATH, logger_conf['filename']))

    try:
        processor_start_server()
    except Exception as e:
        print(e)

    while True:
        time.sleep(5)

    print("Done................")
    if __name__ == '__main__':
        main()
