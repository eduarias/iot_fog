from __future__ import print_function
import unittest
from datetime import timedelta
from cloud_connector.runner import ConfiguratorYaml, Runner
from unittest import mock
from cloud_connector.clouds import CloudAmazonMQTT
from cloud_connector.strategies import Variation


class TestConfiguratorYaml(unittest.TestCase):

    def setUp(self):
        self.config_db = {'user': 'root', 'host': 'localhost', 'password': 'root',
                          'port': 8086, 'database': 'new_values'}
        self.config_devices = {'sim01': {'name': 'sim01'},
                               'sim02': {'name': 'sim02'}}
        self.strategy_variation = {'light': 2, 'temperature': 0.5, 'humidity': 2}

    @mock.patch('cloud_connector.clouds.mqttc', spec=True)
    @mock.patch('cloud_connector.runner.SimDevice', spec=True)
    @mock.patch('cloud_connector.runner.InfluxDB', spec=True)
    def test_configure(self, mock_influxdb, mock_device, mock_cloud):
        conf = ConfiguratorYaml('test/resources/config.yml')

        self.influxdb_should_be_configured(mock_influxdb)

        mock_device.assert_has_calls([mock.call(**self.config_devices['sim01']),
                                      mock.call(**self.config_devices['sim02'])],
                                     any_order=True)

        self.aws_should_be_configured(conf)

    @mock.patch('cloud_connector.runner.InfluxDB', spec=True)
    def test_configure_without_devices(self, mock_influxdb):
        ConfiguratorYaml('test/resources/config_tsdb_only.yml')
        self.influxdb_should_be_configured(mock_influxdb)

    def influxdb_should_be_configured(self, mock_influxdb):
        return mock_influxdb.assert_called_once_with(**self.config_db)

    def aws_should_be_configured(self, conf):
        aws = conf.clouds[0]
        self.assertIsInstance(aws, CloudAmazonMQTT)
        self.assertIsInstance(aws.strategy, Variation)
        aws._mqtt_client.tls_set.assert_called_once_with('./keys/aws-iot-rootCA.crt',
                                                         cert_reqs=2,
                                                         certfile='./keys/cert.pem',
                                                         ciphers=None,
                                                         keyfile='./keys/privkey.pem',
                                                         tls_version=5)
        aws._mqtt_client.connect.assert_called_once_with('A2KYAWFNYZU0I0.iot.eu-west-1.amazonaws.com', 8883,
                                                         keepalive=60)
        aws._mqtt_client.loop_start.assert_called_once_with()
        self.assertEquals(aws.strategy.time_low, timedelta(minutes=1))
        self.assertEquals(aws.strategy.time_high, timedelta(minutes=5))
        self.assertDictEqual(aws.strategy.variability, self.strategy_variation)


# noinspection PyUnusedLocal
@mock.patch('cloud_connector.clouds.mqttc', spec=True)
@mock.patch('cloud_connector.runner.SimDevice', spec=True)
@mock.patch('cloud_connector.runner.InfluxDB', spec=True)
class TestRunner(unittest.TestCase):

    def setUp(self):
        pass

    def test_close_devices(self, mock_influxdb, mock_device, mock_cloud):
        config = ConfiguratorYaml('test/resources/config.yml')
        runner = Runner(config)
        runner.read_interval = 1

        runner.close_devices_connection()

        self.assertEqual(config.devices[0].close.call_count, 2)

    def test_run_happy_path(self, mock_influxdb, mock_device, mock_cloud):

        config = ConfiguratorYaml('test/resources/config.yml')
        config.clouds[0]._conn_flag = True

        runner = Runner(config)
        runner.read_interval = 1

        for device in runner._devices:
            device.name = mock.MagicMock(return_value='mocked')
            device.get_data.return_value = {'temperature': 24.05,
                                            'humidity': 52.31,
                                            'light': 3594.24,
                                            }
        runner.run()

        self.assertEqual(runner._devices[0].get_data.call_count, 2)
        self.assertTrue(runner._sender._tsdb.insert_data.called)
        # TODO - Fix the verify call to insert_data
        # self.assertTrue(runner._cloud_list[0]._mqtt_client.called)

    def test_run_keyboard_error(self, mock_influxdb, mock_device, mock_cloud):
        mock_device.get_data.return_value = {'temperature': 24.05,
                                             'humidity': 52.31,
                                             'light': 3594.24,
                                             }

        config = ConfiguratorYaml('test/resources/config.yml')

        runner = Runner(config)
        runner.read_interval = 1

        for device in runner._devices:
            device.name = mock.MagicMock(return_value='mocked')

        runner._sender._clouds[0].insert_data = mock.MagicMock(side_effect=KeyboardInterrupt)

        runner.run()

        self.assertTrue(runner._devices[0].close.called is True)
