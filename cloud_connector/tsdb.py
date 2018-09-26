"""
Define classes to connect to TSDB.
"""
from abc import ABCMeta, abstractmethod
import logging

from influxdb import InfluxDBClient
import dateutil
import requests
from cloud_connector.cc_exceptions import ConnectionTimeout


INFLUXDB_TIMEOUT = 5


# noinspection PyShadowingNames
class TSDatabase(object):
    """
    Factory pattern class for Time Series Database
    """
    __metaclass__ = ABCMeta

    def __init__(self, host, port, user, password, database):
        if 'parameters' not in locals() or 'parameters' not in globals():
            self.parameters = {}
        self.parameters.update({'host': host,
                                'port': port,
                                'username': user,
                                'password': password,
                                'database': database,
                                'timeout': INFLUXDB_TIMEOUT,
                                })
        self.db = self.connect(self.parameters)
        if not self.db_exists:
            self.create_database()
            logging.info('Database {} created in {}:{}'.format(database, host, port))

    @abstractmethod
    def connect(self, parameters):
        """
        Connect to TSDB
        :param parameters: Parameters to connect the TSDB.
        :return: TSDB client.
        """
        raise NotImplementedError

    @abstractmethod
    def query(self, query):
        """
        Send a query to database
        :param query: Query sentence to execute
        :return: Query result
        """
        raise NotImplementedError

    @property
    def db_exists(self):
        """
        Check if database exists
        :rtype: Boolean
        """
        raise NotImplementedError

    @abstractmethod
    def get_current_time(self):
        """
        Get current TSDB time
        """
        raise NotImplementedError

    @abstractmethod
    def create_database(self):
        """
        Create a TSDB database.
        """
        raise NotImplementedError

    @abstractmethod
    def insert_data(self, data, device_name, clouds=None):
        """
        Insert data in TSDB
        :param data: Data to be inserted.
        :param device_name: Name of the device who insert data.
        :param clouds: Clouds where data was inserted (if any)
        """
        raise NotImplementedError


# noinspection PyShadowingNames
class InfluxDB(TSDatabase):
    """
    Class for InfluxDB database
    :param host: DB hostname or IP address
    :param port: DB port (typically 8086 for InfluxDB)
    :param user: DB user name
    :param password: DB password
    :param database: Database name
    """
    def __init__(self, host, port, user, password, database):
        super(InfluxDB, self).__init__(host, port, user, password, database)

    def connect(self, parameters):
        """
        Make server database connection.
        Number of connection retries is 3 by influxdb client.
        :param parameters: Parameters to connect to database: host, port, username, password, database.
        :type parameters: dict.
        :return: An Influx database client connector.
        :rtype: influxdb.client.InfluxDBClient.
        """
        return InfluxDBClient(**parameters)

    @property
    def db_exists(self):
        """
        Checks if database exists in server.
        :return: True if exists, False if it doesn't.
        :rtype: Boolean.
        :raises: ConnectionError
        """
        try:
            dbs_dicts = self.db.get_list_database()
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            err_msg = 'Unable to connect to InfluxDB {}'.format(self.parameters)
            logging.error(err_msg)
            raise ConnectionTimeout(err_msg)
        dbs_list = [value for dbs_dict in dbs_dicts for key, value in dbs_dict.items()]
        logging.debug('Existing databases are: {}'.format(dbs_list))
        if self.parameters['database'] in dbs_list:
            logging.debug('Database {} already exists in server'.
                          format(self.parameters['database']))
            return True
        else:
            logging.debug('Database {} does not exists in server'.
                          format(self.parameters['database']))
            return False

    def get_current_time(self):
        """
        Get current database time.
        :return: Current database time.
        :rtype: datetime
        """
        rs = self.query('show diagnostics')
        current_time = rs.raw['series'][3]['values'][0][1]
        logging.debug('Current time: {}'.format(current_time))
        # noinspection PyUnresolvedReferences
        return dateutil.parser.parse(current_time)

    def query(self, query):
        """
        Send a query to InfluxDB database.
        :param query: Query sentence to execute.
        :type query: str.
        :return: Query result.
        :rtype: ResultSet.
        """
        return self.db.query(query)

    def create_database(self):
        """
        Create a database with the current object database name
        """
        self.db.create_database(self.parameters['database'])

    def insert_data(self, data, device_name, clouds=None):
        """
        Insert data into database
        :param data: Dictionary of name:values to inserted
        :type data: dict
        :param device_name: Device name
        :type device_name: str
        :param clouds: List of cloud where this data has been inserted
        :type clouds: list.

        To read this tags, query with regex should be used:
             SELECT * FROM <measurement_name> WHERE cloud =~ /.*CloudAmazonMQTT.*/
        """
        if not clouds:
            tags = {}
        else:
            tags = {'cloud': ';'.join(clouds)}
        tags.update({'device': device_name})
        point = {'measurement': 'environment',
                 'fields': data}
        logging.debug('Data to be inserted in {}: {}, tags: {}'.format(self.parameters['database'], point, tags))
        if self.db.write_points([point], tags=tags):
            logging.debug('Data inserted in {}: {}'.format(self.parameters['database'], point))
        else:
            logging.info('Data not inserted {}: {}'.format(self.parameters['database'], point))

