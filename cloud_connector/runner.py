"""
Makes the setup of the classes through configuration and run.
"""
import logging
from threading import Thread

from cloud_connector.data.sender import DataSender
from cloud_connector.devices import SimDevice
from cloud_connector.data.tsdb import InfluxDB
from cloud_connector.data.clouds import CloudAmazonMQTT, CloudThingsIO, CloudPubNub
import sys
import yaml
from sched import scheduler
import time
import traceback
from cloud_connector.cc_exceptions import ConnectionTimeout, ConfigurationError, InputDataError
from cloud_connector.data.strategies import All, Variation, MessageLimit, TimeLimit
import socket

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(threadName)-12s %(name)-12s: %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')

available_strategies = {'All': All,
                        'Variation': Variation,
                        'MessageLimit': MessageLimit,
                        'TimeLimit': TimeLimit,
                        }

available_clouds = {'aws': CloudAmazonMQTT,
                    'thethingsio': CloudThingsIO,
                    'pubnub': CloudPubNub,
                    }


class ConfiguratorYaml(object):
    """
    Reads YAML file and config the application with it content. There will be three sections: devices, tsdb and cloud.
    devices: Configure n OpenMotes with name and ipv6.
    tsdb: Configure an InfluxDB with host, port, user, password and database.
    cloud: Configure n cloud systems with its own parameters and strategy.
    """

    def __init__(self, file_name=None):
        if file_name:
            self._file_name = file_name
        else:
            self._file_name = 'config.yml'

        with open(file_name, 'r') as ymlfile:
            self._config = yaml.safe_load(ymlfile)

        # Initialize read_interval, it will be set in _configure_devices
        self.read_interval = None
        try:
            self.db = self._configure_influxdb()
            self.devices = self._configure_devices()
            self.clouds = self._configure_cloud()
        except Exception as exception:
            msg = '{}: {}'.format(exception.__class__.__name__, exception)
            logging.critical('Configuration Error: {}'.format(msg))
            traceback.print_exc(file=sys.stdout)
            raise ConfigurationError(msg)

    def _configure_influxdb(self):
        """
        Configure InfluxDB object
        :return: InfluxDB object
        :rtype: InfluxDB
        """
        db_config = self._config['tsdb']
        influx = db_config['influxdb']
        try:
            return InfluxDB(**influx)
        except ConnectionTimeout:
            sys.exit('Exiting application.')

    def _configure_devices(self):
        """
        Configure devices
        :return: A list of devices objects initialized
        :rtype: list.
        """
        try:
            devices_config = self._config['devices']
        except KeyError:
            return None
        self.read_interval = devices_config.pop('read_interval')
        devices = []
        for device in devices_config.values():
            devices.append(SimDevice(**device))
        return devices

    def _configure_cloud(self):
        """
        Configure cloud services
        :return: A list of cloud services objects initialized
        :rtype: list.
        """
        try:
            cloud_config = self._config['cloud']
        except KeyError:
            return None

        clouds_list = []
        for cloud, parameters in cloud_config.items():
            if 'strategy' in parameters:
                strategy_config = parameters.pop('strategy')
                strategy_class = available_strategies[strategy_config['type']]
                if 'parameters' in strategy_config:
                    parameters['strategy'] = strategy_class(**strategy_config['parameters'])
            clouds_list.append(available_clouds[cloud](**parameters))
        return clouds_list


class Runner(object):
    """
    Reads the devices
    """

    def __init__(self, configurator):
        """
        Initialize the scheduler
        :param configurator: Configurator class.
        :type configurator: ConfiguratorYaml
        """
        self._scheduler = scheduler(time.time, time.sleep)
        self._devices = configurator.devices
        self._sender = DataSender(configurator)
        self.read_interval = configurator.read_interval
        self._running = False

    def start(self):
        """
        Start running the scheduler
        """
        if self._devices:
            logging.info('Starting runners to read devices')
            self._running = True
            self._periodic(self.run)
            Thread(target=self._scheduler.run).start()
        else:
            logging.info('No devices detected, scheduler not executing.')

    def stop(self):
        """
        Stop scheduler
        """
        self._running = False
        if self._devices:
            for event in self._scheduler.queue:
                self._scheduler.cancel(event)
            self.close_devices_connection()
        logging.info('Scheduler closed.')

    def _periodic(self, action, action_args=()):
        """
        Make a scheduler periodic
        :param action: Function to be run
        :param action_args: Arguments of the function
        :return:
        """
        if self._running:
            self._scheduler.enter(self.read_interval, 1, self._periodic, (action, action_args))
            action(*action_args)

    # noinspection PyBroadException
    def run(self):
        """
        The action that should be schedule. It reads data from devices, inserting in TSDB and cloud service
        """
        start = time.time()
        try:
            logging.debug('Starting new run ...')
            logging.debug('Sending data to cloud services')
            for device in self._devices:
                logging.debug('Connecting to device: {}'.format(device.name))
                self._sender.send_data(device.get_data(), device.name)

        except KeyboardInterrupt:
            self.stop()
        except InputDataError as e:
            logging.error('Unable to read input data. {}'.format(e))
        except Exception as e:
            logging.error('Unexpected error: {0} \n{1}'.format(e, traceback.print_exc()))
        finally:
            logging.debug('Run complete, waiting for next run.')
        logging.info('Run tooks {0:.3f} seconds'.format(time.time() - start))

    def close_devices_connection(self):
        """
        Close devices connection
        """
        logging.info('Closing device connection')
        time.sleep(5)
        if self._devices:
            for device in self._devices:
                device.close()
        logging.info('Device connection close')


if __name__ == '__main__':

    try:
        config = ConfiguratorYaml('config.yml')
        runner = Runner(config)
    except ConfigurationError as e:
        sys.exit('Configuration error, exiting application.')

    try:
        runner.start()
        while True:
            time.sleep(1000)
    except (KeyboardInterrupt, TypeError, KeyError):
        runner.stop()
    except socket.error:
        logging.error('Application is already running, please stop it before run again')
        runner.stop()
