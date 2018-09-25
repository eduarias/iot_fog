"""
Defines devices classes.
"""
import socket
from abc import ABCMeta, abstractmethod
import logging
from contextlib import closing

from random import uniform


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
        Close devices connections (if necessary)
        """
        pass

    @staticmethod
    def find_free_port():
        """Returns an available port to open a connection"""
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            available_port = s.getsockname()[1]
            logging.debug('Available port: {}'.format(available_port))
            return available_port


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
               'humidity': round(uniform(40, 65), 2)}
        return res
