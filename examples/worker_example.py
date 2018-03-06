from celery import Celery
from zc_events.backends import dispatch_task
from examples.settings import BROKER_URL, SERVICE_NAME, EVENTS_EXCHANGE


app = Celery(
    'tests.worker_example',
    broker=BROKER_URL
)

app.config_from_object('examples.settings')


@app.task(name='microservice.event')
def listener(name, data):
    return dispatch_task(name, data)
