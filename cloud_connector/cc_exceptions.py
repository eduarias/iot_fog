"""
Defines custom exceptions.
"""


class ConnectionException(IOError):
    """
    Generic class to define network exceptions
    """

    def __init__(self, *args, **kwargs):
        super(ConnectionException, self).__init__(*args, **kwargs)


class InputDataError(ConnectionException):
    """
    Error when reading data
    """

    def __init__(self, *args, **kwargs):
        super(InputDataError, self).__init__(*args, **kwargs)


class ConnectionTimeout(ConnectionException):
    """
    Connection Timeout exception
    """

    def __init__(self, *args, **kwargs):
        super(ConnectionTimeout, self).__init__(*args, **kwargs)


class ConfigurationError(LookupError):
    """
    Error in configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigurationError, self).__init__(*args, **kwargs)