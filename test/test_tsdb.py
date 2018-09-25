from __future__ import absolute_import, print_function
import unittest
# noinspection PyUnresolvedReferences
import cloud_connector
from cloud_connector.cloud_connector import InfluxDB
from influxdb.resultset import ResultSet
from unittest import mock
from datetime import datetime
from dateutil.tz import tzutc
import requests


# noinspection PyUnusedLocal
class TestsInfluxDB(unittest.TestCase):

    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_init_db_exists(self, client_mocked):

        InfluxDB.db_exists = mock.MagicMock(return_value=True)

        InfluxDB('host', '9999', 'user', 'password', 'mockdb')

        client_mocked.assert_called_once_with(password='password', username='user', database='mockdb',
                                              port='9999', host='host', timeout=5)
        self.assertFalse(client_mocked.create_database.called)

    @staticmethod
    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_init_db_not_exists(client_mocked):
        InfluxDB.db_exists = mock.PropertyMock(return_value=False)

        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')

        client_mocked.assert_called_once_with(password='password', username='user', database='mockdb', port='9999',
                                              host='host', timeout=5)
        influx.db.create_database.assert_called_once_with('mockdb')

    # noinspection PyUnusedLocal
    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_get_current_time(self, mocked_client):
        # Mock response form InfluxDB
        diagnostics = ResultSet({'series': [{'name': 'build',
                                             'columns': ['Branch', 'Build Time', 'Commit', 'Version'],
                                             'values': [
                                                 ['0.12', '', 'e094138084855d444195b252314dfee9eae34cab', '0.12.1']]},
                                            {'name': 'network', 'columns': ['hostname'], 'values': [['raspberrypi']]},
                                            {'name': 'runtime', 'columns': ['GOARCH', 'GOMAXPROCS', 'GOOS', 'version'],
                                             'values': [['arm', 4, 'linux', 'go1.4.3']]},
                                            {'name': 'system', 'columns': ['PID', 'currentTime', 'started', 'uptime'],
                                             'values': [[561, '2016-04-15T21:29:31.886241629Z',
                                                         '2016-04-15T21:21:10.677939741Z', '8m21.2083047s']]}]})
        InfluxDB.query = mock.MagicMock(return_value=diagnostics)

        # Code to test
        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')
        current_time = influx.get_current_time()
        self.assertEqual(current_time, datetime(2016, 4, 15, 21, 29, 31, 886241, tzinfo=tzutc()))

    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_connect_to_db_error(self, mocked_client):
        """
        DB connection error raises a ConnectionError exception
        """
        mocked_client.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.influx_error = InfluxDB('192.168.1.8', '8086', 'root', 'root', 'mockdb')

    @staticmethod
    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_db_not_on_server(mocked_client):
        """
        DB does not exists in server
        """
        mocked_client.return_value.get_list_database.return_value = [{u'name': u'_internal'},
                                                                     {u'name': u'telegraf'},
                                                                     {u'name': u'not_mockdb'}]

        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')
        influx.db.create_database.assert_called_once_with('mockdb')

    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_db_on_server(self, mocked_client):
        """
        DB already exists in server
        """
        mocked_client.return_value.get_list_database.return_value = [{u'name': u'_internal'},
                                                                     {u'name': u'telegraf'},
                                                                     {u'name': u'mockdb'}]

        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')
        self.assertFalse(influx.db.create_database.called)

    @staticmethod
    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_insert_data(mocked_client):
        """
        Data is inserted in database
        """
        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')
        data = {'temperature': 22,
                'humidity': 0.5}

        point = {'measurement': 'environment',
                 'fields': data}

        influx.insert_data(data, 'device_name')

        influx.db.write_points.assert_called_once_with([point], tags={'device': 'device_name'})

    @staticmethod
    @mock.patch('cloud_connector.tsdb.InfluxDBClient', spec=True)
    def test_insert_data_failed(mocked_client):
        """
        Data is not inserted in database
        """
        mocked_client.return_value.write_points.return_value = False
        influx = InfluxDB('host', '9999', 'user', 'password', 'mockdb')
        data = {'temperature': 22,
                'humidity': 0.5}

        point = {'measurement': 'environment',
                 'fields': data}

        influx.insert_data(data, 'device_name')

        influx.db.write_points.assert_called_once_with([point], tags={'device': 'device_name'})

