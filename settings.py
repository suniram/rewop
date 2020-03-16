APP_PATH = 'rewop/'

logger_conf = {
    'filename': 'rewop.log',
    'format': '[%(asctime)s] %(message)s',
    'level': 10
}

rewop_config = {
    'test': True,
    'interval': 20
}

axpert_conf = {
    'vendor_id': 1637,
    'product_id': 20833,
    'baud': 2400,
    'emoncms_node': 'test_inverter',
    'error_reboot_count': 10
}

pylontech_conf = {
    'baud': 115200,
    'emoncms_node': 'test_battery',
    'error_reboot_count': 10
}

econcms_conf = {
    'server': 'emoncms.org',
    'api_key': 'your_econcms_api_key'
}

ifttt_conf = {
    'server': 'maker.ifttt.com',
    'api_key': 'your_ifttt_api_key'
}

pool_pump_conf = {
    'soc_high': 90,
    'soc_low': 80,
    'load_high': 2000,
    'pv_low': -500,
    'pv_high': 800,
    'on_trigger': 'swembad_pomp_aan',
    'off_trigger': 'swembad_pomp_af',
    'pv_low_delay': 0,
    'on_delay': 0,
}

inverter_conf = {
    'load_shedding_to_utility_end': 8,
    'load_shedding_to_utility_start': 17
}
