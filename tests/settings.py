from os import environ
from zc_events.backends import RabbitMqFanoutBackend

AWS_ACCESS_KEY_ID = 'aws-access-key'
AWS_SECRET_ACCESS_KEY = 'aws-secret-key'
SECRET_KEY = 'test-secret-key'
SERVICE_NAME = 'zc-events-test'
BROKER_URL = 'amqp://guest:guest@rabbitmq:5672/%2F'
EVENTS_REDIS_URL = environ.get('REDIS_URL', 'redis://redis:6379')
STAGING_NAME = 'test'
EVENTS_EXCHANGE = 'test-exchange'
NOTIFICATIONS_EXCHANGE = 'test-notification-exchange'


# Used as the remote function to call during tests
def add(request):
    data = request.data
    return data['x'] + data['y']


RPC_BACKEND = RabbitMqFanoutBackend()
JOB_MAPPING = {'add': add}
