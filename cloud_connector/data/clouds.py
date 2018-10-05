"""
Classes to interact with cloud systems.
"""
import json
from abc import ABCMeta, abstractmethod
import logging
import paho.mqtt.client as mqttc
import ssl
from retry import retry
from cloud_connector.cc_exceptions import ConnectionException
from cloud_connector.data.strategies import All
from cloud_connector.third_party.thethingsAPI import thethingsiO
from pubnub import Pubnub

QOS_LEVEL = 1
CLOUD_RETRIES = 7
CLOUD_RETRY_WAIT = 2
BASE_TOPIC = 'motes'


# noinspection PyShadowingNames
class CloudServiceBase(object):
    """
    Factory pattern class for cloud services
    """
    __metaclass__ = ABCMeta

    def __init__(self, strategy=None):
        """
        :param strategy: Strategy object to send data to cloud.
        :type strategy: StrategyBase.
        """
        self.name = 'Unknown'
        if not strategy:
            self.strategy = All()
        else:
            self.strategy = strategy

    def insert_data(self, data, device_name):
        """
        Insert data into cloud service if strategy allows to.
        :param data: Data to be inserted
        :type data: dict.
        :param device_name:
        :type device_name:str.
        :return: Class name
        :rtype: str.
        """
        if self.strategy.has_to_send_data(data):
            self._send_data(data, device_name)
            return self.__class__.__name__
        else:
            logging.debug('Data is not going to be updated to {} cloud service.'.format(self.name))
            return False

    @abstractmethod
    def _send_data(self, data, device_name):
        """
        Send the data to the cloud
        :param data: Data to be inserted
        :type data: dict.
        :param device_name:
        :type device_name:str.
        """
        raise NotImplementedError


# noinspection PyShadowingNames
class CloudAmazonMQTT(CloudServiceBase):
    """
    Configures Amazon as Cloud Service using MQTT
    """

    def __init__(self, host, port, ca_path, cert_path, key_path, strategy=None):
        """
        Initialize the class
        :param host: AWS host
        :type host: str
        :param port: AWS port
        :type port: str
        :param ca_path: String path to Certificate Authority certificate
        :type ca_path: str
        :param cert_path: PEM encoded client certificate
        :type cert_path: str
        :param key_path: PEM encoded private keys
        :type key_path: str
        :param strategy: Strategy object to send data to cloud.
        :type strategy: StrategyBase.
        """
        super(CloudAmazonMQTT, self).__init__(strategy)
        self.name = 'AWS IoT'
        self._conn_flag = False

        self._mqtt_client = mqttc.Client()
        self._configure_mqtt_client(ca_path, cert_path, key_path)
        self._mqtt_client.connect(host, int(port), keepalive=60)

        self._mqtt_client.loop_start()

    def _configure_mqtt_client(self, ca_path, cert_path, key_path):
        """
        Configure MQTT client with AWS keys
        :param ca_path: String path to Certificate Authority certificate
        :type ca_path: str
        :param cert_path: PEM encoded client certificate
        :type cert_path: str
        :param key_path: PEM encoded private keys
        :type key_path: str
        """
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        # Use PROTOCOL_TLSv1 to ensure compatibility with python < 2.7.9
        self._mqtt_client.tls_set(ca_path,
                                  certfile=cert_path,
                                  keyfile=key_path,
                                  cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLSv1_2,
                                  ciphers=None)

    # noinspection PyUnusedLocal
    def _on_connect(self, client, userdata, flags, rc):
        """
        on_connect method passed to MQTT client
        """
        self._conn_flag = True
        logging.debug('Amazon connection returned result: {}'.format(rc))

    # noinspection PyUnusedLocal
    @staticmethod
    def _on_message(client, userdata, msg):
        """
        on_message method passed to MQTT client
        """
        logging.debug('msg.topic {}'.format(msg.payload))

    @retry(ConnectionException, tries=CLOUD_RETRIES, delay=CLOUD_RETRY_WAIT)
    def _send_data(self, data, device_name):
        logging.debug('Trying to send MQTT message')
        if not self._conn_flag:
            logging.error('Not connected to AWS MQTT')
            raise ConnectionException('Unable to connect with AWS IoT')
        topic = '{}/{}'.format(BASE_TOPIC, device_name)
        data_json = self._convert_data_to_json(data)
        self._mqtt_client.publish(topic,
                                  data_json,
                                  qos=QOS_LEVEL)
        logging.info('Sent to AWS: {}:{}'.format(topic, data_json))

    @staticmethod
    def _convert_data_to_json(data):
        return json.dumps(data)


class CloudThingsIO(CloudServiceBase):
    """
    Configures thethings.io as cloud service
    """

    def __init__(self, tokens, strategy=None):
        """
        Initialize class
        :param tokens: Dictionary of devices and tokens.
        :type tokens: dict.
        :param strategy: Strategy object to send data to cloud.
        :type strategy: StrategyBase.
        """
        super(CloudThingsIO, self).__init__(strategy=strategy)
        self.name = 'thethings.io'
        self._tokens = tokens
        self._thethings_connector = {}
        for device_name, token in tokens.items():
            self._thethings_connector[device_name] = thethingsiO(token)

    def _send_data(self, data, device_name):
        """
        Insert data into thethings.io
        :param data: Data to be sent.
        :param device_name: dict.
        :return: Class name.
        :rtype: str.
        """
        try:
            tt = self._thethings_connector[device_name]
            for variable, info in data.items():
                tt.addVar(variable, info)
            try:
                logging.debug('Sending data to thethings.iO')
                response_code = tt.write()
                logging.info('Sent to thethings.io with response code {}: {}:{}'.format(response_code, device_name, data))
            except Exception:
                logging.error('Unable to send data to thethings.io')
        except KeyError:
            logging.warning('Device <{0}> not found on thethingsio'.format(device_name))


class CloudPubNub(CloudServiceBase):
    """
    PubNub cloud service connector
    """
    def __init__(self, publish_key, subscribe_key, strategy=None):
        """

        :param publish_key: Publish key
        :type publish_key: str.
        :param subscribe_key: Subscribe key
        :type subscribe_key: str
        :param strategy: Strategy object to send data to cloud.
        :type strategy: StrategyBase.
        """
        super(CloudPubNub, self).__init__(strategy=strategy)
        self.name = 'pubnub'
        self.pubnub = Pubnub(publish_key=publish_key, subscribe_key=subscribe_key)
        self.pubnub.subscribe(channels="iot_data", callback=self._callback_subscribe, error=self._error)

    @staticmethod
    def _callback_subscribe(message, channel):
        """
        Callback method for subscribe.
        """
        logging.info('PubNub reads: {}'.format(message))

    @staticmethod
    def _error(message):
        """
        Error method for subscribe.
        """
        logging.error('PubNub: {}'.format(message))

    @staticmethod
    def _callback_publish(message):
        """
        Callback method for publish.
        """
        logging.info('PubNub: {}'.format(message))

    def _send_data(self, data, device_name):
        self.pubnub.publish("iot_data", data, callback=self._callback_publish, error=self._callback_publish)

