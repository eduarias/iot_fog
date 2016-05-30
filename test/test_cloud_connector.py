from __future__ import print_function
import unittest
from datetime import timedelta
# noinspection PyUnresolvedReferences
import cloud_connector
# noinspection PyUnresolvedReferences
from cloud_connector.cloud_connector import ConfiguratorYaml, Runner
import mock as mock
# noinspection PyUnresolvedReferences
from cloud_connector.clouds import CloudAmazonMQTT
# noinspection PyUnresolvedReferences
from cloud_connector.strategies import Variation


class TestConfiguratorYaml(unittest.TestCase):

    @mock.patch('cloud_connector.clouds.mqttc', spec=True)
    @mock.patch('cloud_connector.cloud_connector.Motes', spec=True)
    @mock.patch('cloud_connector.cloud_connector.InfluxDB', spec=True)
    def test_configure(self, mock_influxdb, mock_device, mock_cloud):
        config_db = {'user': 'root', 'host': 'localhost', 'password': 'root',
                     'port': 8086, 'database': 'new_values'}
        config_devices = {'mote01': {'name': 'mote01', 'ipv6': 'bbbb::12:4b00:0615:a557'},
                          'mote02': {'name': 'mote02', 'ipv6': 'bbbb::12:4b00:0615:a558'}}
        strategy_variation = {'light': 2, 'temperature': 0.5, 'humidity': 2}

        conf = ConfiguratorYaml('test/resources/config.yml')

        mock_influxdb.assert_called_once_with(**config_db)
        mock_device.assert_has_calls([mock.call(**config_devices['mote01']),
                                      mock.call(**config_devices['mote02'])],
                                     any_order=True)

        aws = conf.cloud_list[0]
        self.assertIsInstance(aws, CloudAmazonMQTT)
        self.assertIsInstance(aws.strategy, Variation)
        aws._mqtt_client.tls_set.assert_called_once_with('./keys/aws-iot-rootCA.crt',
                                                         cert_reqs=2,
                                                         certfile='./keys/cert.pem',
                                                         ciphers=None,
                                                         keyfile='./keys/privkey.pem',
                                                         tls_version=5)
        aws._mqtt_client.connect.assert_called_once_with('A2KYAWFNYZU0I0.iot.eu-west-1.amazonaws.com', 8883, keepalive=60)
        aws._mqtt_client.loop_start.assert_called_once_with()
        self.assertEquals(aws.strategy.time_low, timedelta(minutes=1))
        self.assertEquals(aws.strategy.time_high, timedelta(minutes=5))
        self.assertDictEqual(aws.strategy.variability, strategy_variation)


# noinspection PyUnusedLocal
@mock.patch('cloud_connector.clouds.mqttc', spec=True)
@mock.patch('cloud_connector.cloud_connector.Motes', spec=True)
@mock.patch('cloud_connector.cloud_connector.InfluxDB', spec=True)
class TestRunner(unittest.TestCase):

    def setUp(self):
        pass

    def test_close_devices(self, mock_influxdb, mock_device, mock_cloud):
        config = ConfiguratorYaml('test/resources/config.yml')
        runner = Runner(config)
        runner.read_interval = 1

        runner.close_devices_connection()

        self.assertEqual(config.device_list[0].close.call_count, 2)

    def test_run_happy_path(self, mock_influxdb, mock_device, mock_cloud):

        config = ConfiguratorYaml('test/resources/config.yml')
        config.cloud_list[0]._conn_flag = True

        runner = Runner(config)
        runner.read_interval = 1

        for device in runner._device_list:
            device.name = mock.MagicMock(return_value='mocked')
            device.get_data.return_value = {'temperature': 24.05,
                                            'humidity': 52.31,
                                            'light': 3594.24,
                                            }
        runner.run()

        self.assertEqual(runner._device_list[0].get_data.call_count, 2)
        self.assertTrue(runner._tsdb.insert_data.called)
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

        for device in runner._device_list:
            device.name = mock.MagicMock(return_value='mocked')

        runner._cloud_list[0].insert_data = mock.MagicMock(side_effect=KeyboardInterrupt)

        runner.run()

        self.assertTrue(runner._device_list[0].close.called is True)
