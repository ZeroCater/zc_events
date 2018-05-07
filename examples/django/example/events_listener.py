import logging
from example import celery_app as app
from zc_events.backends import rabbitmq_dispatch_task

logger = logging.getLogger('django')


@app.task(name='microservice.event')
def microservice_event(event_type, *args, **kwargs):
    if len(args) == 1:
        responded, dispatched_task = rabbitmq_dispatch_task(event_type, args[0])
