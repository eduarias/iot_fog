import unittest
from unittest import mock

from cloud_connector.cloud_connector import SimDevice


class TestMotes(unittest.TestCase):

    @mock.patch('cloud_connector.cloud_connector.SimDevice', spec=True)
    def test_get_data(self, mock_device):
        self.mote = SimDevice('mote01')

        res = self.mote.get_data()

        expected_result = {'temperature': 24.05,
                           'humidity': 52.31,
                           }
        self.assertDictEqual(res, expected_result)
