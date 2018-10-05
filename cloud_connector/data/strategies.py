"""
Defines cloud strategy classes
"""
from __future__ import division
import logging
from abc import ABCMeta

from datetime import datetime, timedelta


class StrategyBase(object):
    """
    Base class to define strategies.
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        self._last_data_sent = None

    def has_to_send_data(self, data):
        """
        According to the strategy, does the data has to be sent to cloud system?
        :param data: New data.
        :return: If the strategy has t be sent or not.
        :rtype: bool.
        """
        raise NotImplementedError

    @property
    def last_data_sent(self):
        """
        A property with the last data  that has been sent to cloud and timestamp, in order to compare.
        :return: A dictionary with timestamp and last data sent to cloud.
        :rtype: dict
        """
        return self._last_data_sent

    @last_data_sent.setter
    def last_data_sent(self, data):
        self._last_data_sent = {'timestamp': datetime.now(),
                                'data': data
                                }

    def ok_to_insert_data(self, data):
        """
        To avoid repetition, it does the necessary actions when data has to be sent.
        :param data: Data to send.
        :type data: dict.
        :return: True
        :rtype: bool.
        """
        self.last_data_sent = data
        return True

    def get_time_since_last_send(self):
        """
        Get time from last data send.
        :return: timedelta.
        """
        return datetime.now() - self.last_data_sent['timestamp']


class All(StrategyBase):
    """
    Defines an strategy of send all data.
    """

    def has_to_send_data(self, data):
        return self.ok_to_insert_data(data)


class Variation(StrategyBase):
    """
    Defines an strategy with a higher and lower update rates and a variability.
    """
    def __init__(self, time_low, time_high, variability):
        """
        :param time_low: Lower time to update in seconds.
        :param time_high: Higher time to update in seconds.
        :param variability: Variability parameters for each variable.
        :type variability: dict.
        """
        super(Variation, self).__init__()
        self.time_low = timedelta(seconds=time_low)
        self.time_high = timedelta(seconds=time_high)
        self.variability = variability

    def has_to_send_data(self, data):

        if not self.last_data_sent:
            return self.ok_to_insert_data(data)

        time_since_last_sent = self.get_time_since_last_send()

        if time_since_last_sent > self.time_high:
            return self.ok_to_insert_data(data)

        if time_since_last_sent < self.time_low:
            return False

        last_data_measures = self.last_data_sent['data']
        for measure, value in data.items():
            try:
                if abs(last_data_measures[measure] - value) > self.variability[measure]:
                    return self.ok_to_insert_data(data)
            except KeyError:
                logging.error('Measure {} not defined in strategy'.format(measure))

        return False


class TimeLimit(StrategyBase):
    """
    Set a lower time limit for messages
    """
    def __init__(self, seconds):
        super(TimeLimit, self).__init__()
        self.seconds_between_messages = timedelta(seconds=seconds)

    def has_to_send_data(self, data):
        if not self.last_data_sent:
            return self.ok_to_insert_data(data)
        if self.get_time_since_last_send() < self.seconds_between_messages:
            return False
        else:
            return self.ok_to_insert_data(data)


class MessageLimit(TimeLimit):
    """
    Limit the amount of messages per day
    """
    def __init__(self, messages_per_day):
        seconds = 86400 / messages_per_day
        super(MessageLimit, self).__init__(seconds)
