import logging
from .client import EventClient

# See the python docs for why
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    'EventClient'
]
