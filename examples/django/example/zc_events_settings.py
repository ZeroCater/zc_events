from zc_events.backends import RabbitMqFanoutBackend
from example.views import AddView
from example.settings import *


JOB_MAPPING = {
    'add_drf': AddView
}
RPC_BACKEND = RabbitMqFanoutBackend()
