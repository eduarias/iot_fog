import unittest
# noinspection PyUnresolvedReferences
import cloud_connector
from cloud_connector.cloud_connector import Motes
import mock as mock


class TestMotes(unittest.TestCase):
    def setUp(self):
        self.ipv6 = 'bbbb::12:4b00:0615:a000'

    @mock.patch('cloud_connector.devices.coap', spec=True)
    def test_get_data(self, mocked_coap):
        self.mote = Motes('mote01', self.ipv6)
        self.mote._conn.GET.side_effect = [[103, 80], [119, 108], [9, 156]]

        res = self.mote.get_data()

        self.mote._conn.GET.asset_has_calls(['coap://[{0}]/s/t'.format(self.ipv6),
                                             'coap://[{0}]/s/h'.format(self.ipv6),
                                             ])

        expected_result = {'temperature': 24.05,
                           'humidity': 52.31,
                           'light': 3594.24,
                           }
        self.assertDictEqual(res, expected_result)
