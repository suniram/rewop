import json
import logging
import os
import time
from datetime import datetime
from urllib import request

from settings import logger_conf, APP_PATH


def main():
    logging.basicConfig(
        format=logger_conf['format'],
        filename='{}/{}'.format(APP_PATH, 'watchdog.log'))

    log = logging.getLogger('WatchDog')
    time.sleep(340)
    while True:
        try:
            url = 'https://emoncms.org/input/get/system&apikey=api_key'
            r = request.urlopen(url, timeout=10)
            system_data = json.load(r)
            log.debug("WatchDog {}".format(system_data))
            last_data_time = datetime.fromtimestamp(system_data['battery_mode']['time'])

            duration = (datetime.now() - last_data_time).total_seconds() / 60

            log.info('Duration {}'.format(duration))

            if duration > 5:
                log.info('Rewop 5 min time, restarting system {}'.format(duration))
                os.system('reboot')

        except Exception as e:
            log.error("Unable to determine load shedding status {}".format(e))
        time.sleep(600)


if __name__ == '__main__':
    main()
