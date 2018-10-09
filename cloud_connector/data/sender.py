"""
Class to handle the send data to TSDB and clouds.
"""

import logging


class DataSender(object):
    """
    Store and send data to cloud.
    """

    def __init__(self, configurator):
        """
        Initialize the mechanisms to store and send data
        :param configurator: Configurator class.
        :type configurator: ConfiguratorYaml
        """
        self._tsdb = configurator.db
        self._clouds = configurator.clouds

    def send_data(self, data, device_name):
        """
        Save data in TSDB and cloud services
        :param data:
        :param device_name:
        :return:
        """
        for key, value in data.items():
            if isinstance(value, int):
                data[key] = float(value)
        cloud_names = []
        if self._clouds:
            cloud_names = [cloud.insert_data(data, device_name) for cloud in self._clouds]
            cloud_names = [cloud for cloud in cloud_names if cloud]  # Filter all clouds that have not send data
        logging.debug('Inserting data into TSDB')
        self._tsdb.insert_data(data, device_name, cloud_names)
