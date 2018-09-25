import unittest
import socket

from cloud_connector.cloud_connector import SimDevice


class TestDevice(unittest.TestCase):

    def test_get_data(self):
        self.mote = SimDevice('mote01')

        res = self.mote.get_data()

        self.assertTrue(20 <= res['temperature'] <= 25)
        self.assertTrue(40 <= res['humidity'] <= 65)

    def test_find_free_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.mote = SimDevice('mote01')
        port = self.mote.find_free_port()
        try:
            s.bind(('127.0.0.1', port))
        except socket.error:
            self.fail('Port already in use')
