"""
Defines devices classes.
"""
import random
from abc import ABCMeta, abstractmethod
import logging

from random import uniform
from coap import coap, coapException
from cc_exceptions import InputDataError


class DeviceBase(object):
    """
    Factory pattern class to define a device.
    :param name: Device name.
    :type name: str.
    :param measurements: Type of measures.
    :type measurements str.
    """
    __metaclass__ = ABCMeta

    def __init__(self, name, measurements):
        self.name = name
        self.measurements = measurements

    @abstractmethod
    def get_data(self):
        """
        Get data from device.
        :return: A dictionary with the values of device data.
        :rtype: dict.
        """
        raise NotImplementedError

    def close(self):
        """
        Close devices connections
        """
        pass


class SimDevice(DeviceBase):
    """
    Define a simulation device that returns random temperatures from 20 to 25 and humidity for 0.4 to 0.6
    :param name: Device name.
    :type name: str.
    """

    def __init__(self, name):
        super(SimDevice, self).__init__(name, measurements='sims')

    def get_data(self):
        """
        Get simulated data from device.
        :return: A dictionary with the random values for temperature and humidity.
        :rtype: dict.
        """
        res = {'temperature': round(uniform(20, 25), 2),
               'humidity': round(uniform(0.4, 0.6), 2)}
        return res


class Motes(DeviceBase):
    """
    Define an OpenMote device that returns temperatures and humidity using coap
    :param name: Device name.
    :type name: str.
    :param ipv6: IPv6 address of the device
    :type ipv6: str.
    """
    SENSORS_PATHS = {'temperature': 's/t',
                     'humidity': 's/h',
                     'light': 's/l',
                     }

    def __init__(self, name, ipv6):
        super(Motes, self).__init__(name, measurements='environment')
        self._ipv6 = ipv6
        self._conn = coap.coap(udpPort=random.randrange(5683, 6000))

    def get_data(self):
        """
        Get data from OpenMote.
        :return: A dictionary with the OpenMote values for temperature and humidity.
        :rtype: dict.
        """
        res = {'temperature': self.get_temperature(),
               'humidity': self.get_humidity(),
               'light': self.get_light(),
               }
        return res

    def get_temperature(self):
        """
        Get temperature values.
        :return: Temperature value in Celsius degrees
        :rtype: float.
        """
        value = self.get_resource_coap('temperature')
        return self.temperature_converter(value)

    @staticmethod
    def temperature_converter(mote_value):
        """
        Temperature converter from OpenMote values
        :param mote_value: List of values returned by OpenMote.
        :type mote_value: list.
        :return: Temperature value in Celsius degrees.
        :rtype: float.
        """
        read_temperature = (mote_value[0] << 8) + mote_value[1]
        temperature = round(-46.86 + 175.72 * read_temperature / 65536, 2)
        return temperature

    def get_humidity(self):
        """
        Get humidity values.
        :return: Humidity value in %
        :rtype: float.
        """
        value = self.get_resource_coap('humidity')
        return self.humidity_converter(value)

    @staticmethod
    def humidity_converter(mote_value):
        """
        Humidity converter from OpenMote values
        :param mote_value: List of values returned by OpenMote.
        :type mote_value: list.
        :return: Humidity value.
        :rtype: float.
        """
        read_humidity = (mote_value[0] << 8) + mote_value[1]
        humidity = round(-6.0 + 125.0 * read_humidity / 65536, 2)
        return humidity

    def get_light(self):
        """
        Get light values.
        :return: Light value in luxs
        :rtype: float.
        """
        value = self.get_resource_coap('light')
        return self.light_converter(value)

    @staticmethod
    def light_converter(mote_value):
        """
        Humidity converter from OpenMote values
        According to data sheet: http://datasheets.maximintegrated.com/en/ds/MAX44009.pdf
        Lux = (2**(exponent) x mantissa) x 0.045
        :param mote_value: List of values returned by OpenMote.
        :type mote_value: list.
        :return: Lux value.
        :rtype: float.
        """
        light = ((2 ** mote_value[0]) * mote_value[1]) * 0.045
        return round(light, 2)

    def get_resource_coap(self, resource):
        """
        Get a CoAP GET petition response for a sensor
        :param resource: type of value, must be registered in SENSORS_PATH (temperature, humidity)
        :type resource: str
        :return:
        """
        url_base = 'coap://[{0}]/{1}'
        url = url_base.format(self._ipv6, self.SENSORS_PATHS[resource])
        logging.debug('Calling read values from {}'.format(url))
        try:
            res = self._conn.GET(url)
            logging.debug('Read value of {0}: {1}'.format(resource, res))
        except coapException.coapTimeout as e:
            logging.error('CoAP timeout. {}'.format(e.reason))
            raise InputDataError(e.reason)

        return res

    def close(self):
        """
        Close CoAP connections
        """
        self._conn.close()
