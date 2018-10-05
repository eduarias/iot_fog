import json
import unittest
from cloud_connector.data.clouds import CloudAmazonMQTT, QOS_LEVEL, CloudThingsIO, thethingsiO, CloudPubNub
from unittest import mock
from cloud_connector.cc_exceptions import ConnectionException
import ssl


# noinspection PyUnusedLocal
class TestAWSMQTT(unittest.TestCase):
    def setUp(self):
        self.aws_host = "aaaaaa.iot.eu-west-1.amazonaws.com"
        self.aws_port = '8883'
        self.ca_path = "../keys/aws-iot-rootCA.crt"
        self.cert_path = "../keys/cert.pem"
        self.key_path = "../keys/privkey.pem"

    @mock.patch('paho.mqtt.client.Client', spec=True)
    def test_client_connects(self, mocked_mqttc):
        cloud = CloudAmazonMQTT(self.aws_host, self.aws_port, self.ca_path,
                                self.cert_path, self.key_path)

        cloud._mqtt_client.tls_set.assert_called_once_with(self.ca_path,
                                                           certfile=self.cert_path,
                                                           keyfile=self.key_path,
                                                           cert_reqs=ssl.CERT_REQUIRED,
                                                           tls_version=ssl.PROTOCOL_TLSv1_2,
                                                           ciphers=None)
        cloud._mqtt_client.connect.assert_called_once_with(self.aws_host, int(self.aws_port), keepalive=60)

    @mock.patch('paho.mqtt.client.Client', spec=True)
    def test_insert_data(self, mocked_mqttc):
        data = {'temperature': 22,
                'humidity': 0.5}
        cloud = CloudAmazonMQTT(self.aws_host, self.aws_port, self.ca_path,
                                self.cert_path, self.key_path)
        cloud._conn_flag = mock.MagicMock(return_value=True)

        cloud.insert_data(data, 'device_name')

        cloud._mqtt_client.publish.assert_any_call('motes/device_name',
                                                   json.dumps(data),
                                                   qos=QOS_LEVEL)

    @mock.patch('paho.mqtt.client.Client', spec=True)
    def test_insert_data_error(self, mocked_mqttc):
        data = {'temperature': 22,
                'humidity': 0.5}
        cloud = CloudAmazonMQTT(self.aws_host, self.aws_port, self.ca_path,
                                self.cert_path, self.key_path)
        cloud._conn_flag = False

        with self.assertRaises(ConnectionException):
            cloud.insert_data(json.dumps(data), 'device_name')


# noinspection PyUnusedLocal
class TestCloudThingsIO(unittest.TestCase):
    def setUp(self):
        self.tokens = {'mote01': 'l0M5BEaDdzt40VqGy6omEqZyDY62CxA6XwCJiitest1',
                       'mote02': 'l0M5BEaDdzt40VqGy6omEqZyDY62CxA6XwCJiitest2'}

    def test_client_connects(self):
        cloud = CloudThingsIO(self.tokens)

        self.assertEqual(len(cloud._thethings_connector), 2)
        self.assertIsInstance(cloud._thethings_connector['mote02'], thethingsiO)

    @mock.patch('cloud_connector.data.clouds.thethingsiO', spec=True)
    def test_insert_data(self, mocked_thethingsiO):
        data = {'temperature': 22,
                'humidity': 0.5}
        cloud = CloudThingsIO(self.tokens)
        cloud.insert_data(data, 'mote01')

        self.assertDictEqual(cloud._tokens, self.tokens)
        self.assertEqual(len(cloud._thethings_connector), 2)


class TestPubNub(unittest.TestCase):
    def setUp(self):
        self.publisher_key = 'pub-c-b3d6a6e3-ce77-4a89-9e0b-49e52xxxxxxx'
        self.subscriber_key = 'sub-c-d74fa040-16f4-11e6-8bc8-0619fxxxxxxx'

    @mock.patch('cloud_connector.data.clouds.Pubnub', spec=True)
    def test_insert_data(self, mocked_pubnub):
        data = {'temperature': 22,
                'humidity': 0.5}
        cloud = CloudPubNub(self.publisher_key, self.subscriber_key)
        cloud.insert_data(data, 'mote01')
        mocked_pubnub.assert_called_once_with(subscribe_key=self.subscriber_key, publish_key=self.publisher_key)
        cloud.pubnub.subscribe.assert_called_once()
        self.assertDictEqual(cloud.pubnub.publish.call_args[0][1], data)