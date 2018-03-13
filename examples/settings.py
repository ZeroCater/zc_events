from kombu import Exchange, Queue
from examples.worker_tasks import add
from zc_events.backends import RabbitMqFanoutBackend

AWS_ACCESS_KEY_ID = 'aws-access-key'
AWS_SECRET_ACCESS_KEY = 'aws-secret-key'
SECRET_KEY = 'test-secret-key'
SERVICE_NAME = 'zc-events-test'
BROKER_URL = 'amqp://guest:guest@rabbitmq:5672/%2F'
EVENTS_REDIS_URL = 'redis://redis:6379'
STAGING_NAME = 'test'
EVENTS_EXCHANGE = 'test-exchange'
NOTIFICATIONS_EXCHANGE = 'test-notification-exchange'

events_exchange = Exchange(EVENTS_EXCHANGE, type='fanout')

CELERY_QUEUES = (
    # Add this line
    Queue(SERVICE_NAME + '-events', events_exchange, queue_arguments={'x-max-priority': 10}, routing_key='#'),
)

CELERY_ROUTES = ('zc_events.routers.TaskRouter',)

JOB_MAPPING = {'add': add}
RPC_BACKEND = RabbitMqFanoutBackend()
