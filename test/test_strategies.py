from unittest import TestCase
import datetime
from cloud_connector.data.strategies import All, Variation, MessageLimit, TimeLimit


class TestAll(TestCase):

    def test_all_data_is_sent(self):
        strategy = All()
        data = {'temp': 25}
        self.assertTrue(strategy.has_to_send_data(data))
        self.assertDictEqual(strategy.last_data_sent['data'], data)


class TestVariation(TestCase):

    @staticmethod
    def strategy_send_data_ok(sent_data, input_data):
        strategy = Variation(30, 300, {'temp': 1, 'hum': 3})
        strategy._last_data_sent = sent_data
        return strategy.has_to_send_data(input_data)

    def test_has_to_send_data_time_higher(self):
        sent_data = {'timestamp': datetime.datetime.now() - datetime.timedelta(minutes=6),
                     'data': {'temp': 25, 'hum': 50}
                     }
        input_data = {'temp': 25, 'hum': 50}

        self.assertTrue(self.strategy_send_data_ok(sent_data, input_data))

    def test_has_to_send_data_time_lower(self):
        sent_data = {'timestamp': datetime.datetime.now() - datetime.timedelta(seconds=10),
                     'data': {'temp': 25, 'hum': 50}
                     }
        input_data = {'temp': 25, 'hum': 50}

        self.assertFalse(self.strategy_send_data_ok(sent_data, input_data))

    def test_has_to_send_data_variation(self):
        sent_data = {'timestamp': datetime.datetime.now() - datetime.timedelta(minutes=2),
                     'data': {'temp': 25, 'hum': 50}
                     }

        input_data = {'temp': 30, 'hum': 50}

        self.assertTrue(self.strategy_send_data_ok(sent_data, input_data))

    def test_has_to_send_data_not(self):
        sent_data = {'timestamp': datetime.datetime.now() - datetime.timedelta(minutes=3),
                     'data': {'temp': 25, 'hum': 50}
                     }

        input_data = {'temp': 25, 'hum': 50}

        self.assertFalse(self.strategy_send_data_ok(sent_data, input_data))

    def test_no_previous_data(self):

        input_data = {'temp': 25, 'hum': 50}
        strategy = Variation(30, 300, {'temp': 1, 'hum': 3})

        self.assertTrue(strategy.has_to_send_data(input_data))

    def test_not_expected_measure(self):
        sent_data = {'timestamp': datetime.datetime.now() - datetime.timedelta(minutes=2),
                     'data': {'temp': 25, 'light': 50}
                     }

        input_data = {'temp': 30, 'light': 50}

        self.assertTrue(self.strategy_send_data_ok(sent_data, input_data))


class TestTimeLimit(TestCase):

    def test_send_data(self):
        strategy = self.configure_strategy(seconds=180)
        input_data = {'temp': 30, 'light': 50}

        self.assertTrue(strategy.has_to_send_data(input_data))

    def test_not_send_data(self):
        strategy = self.configure_strategy(seconds=3)
        input_data = {'temp': 30, 'light': 50}

        self.assertFalse(strategy.has_to_send_data(input_data))

    @staticmethod
    def configure_strategy(seconds):
        strategy = TimeLimit(10)
        strategy._last_data_sent = {'timestamp': datetime.datetime.now() - datetime.timedelta(seconds=seconds),
                                    'data': {'temp': 25, 'hum': 50}
                                    }
        return strategy


class TestMessageLimit(TestCase):

    def test_seconds_to_send_message(self):
        strategy = MessageLimit(10000)
        self.assertEqual(strategy.seconds_between_messages, datetime.timedelta(seconds=8.64))

    def test_send_data(self):
        strategy = self.configure_strategy(seconds=180)
        input_data = {'temp': 30, 'light': 50}

        self.assertTrue(strategy.has_to_send_data(input_data))

    def test_not_send_data(self):
        strategy = self.configure_strategy(seconds=3)
        input_data = {'temp': 30, 'light': 50}

        self.assertFalse(strategy.has_to_send_data(input_data))

    @staticmethod
    def configure_strategy(seconds):
        strategy = MessageLimit(10000)
        strategy._last_data_sent = {'timestamp': datetime.datetime.now() - datetime.timedelta(seconds=seconds),
                                    'data': {'temp': 25, 'hum': 50}
                                    }
        return strategy
