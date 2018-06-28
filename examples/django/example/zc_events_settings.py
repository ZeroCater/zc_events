from zc_events.backends import RabbitMqFanoutBackend
from example.views import AddView, LookupView
from example.settings import *


JOB_MAPPING = {
    'add_drf': AddView,
    'lookup_drf': LookupView
}
RPC_BACKEND = RabbitMqFanoutBackend()
