# zc_events

# Long term plan

The long term plan is to simplify this library as much as possible. This will be done in several stages:

- [x] Add http verbs to `EventClient`
- [x] Deprecate all other methods on `EventClient`, except `email` related ones.
- [x] Decouple `EventClient` from any particular backend to send events.
- [x] Move over sending events through Django Rest Framework.
- [x] Move over sending specific `email` type of events.
- [ ] Create a `celery` backend to stop placing things directly on rabbitmq, with sane defaults.
- [ ] Major version change that removes deprecated methods and classes.

Each of the above represent potential releases.

## Vision

This library should be as simple as possible, with a standard interface that is decoupled from the transport mechanism underlying any event system (RabbitMQ, Celery, Redis, HTTPS, etc.).

## Example based goals

```python
# Server side
def add(request):
    data = request.data
    return {
        'answer': data['x'] + data['y']
    }
```

### Fire and forget

```python
# Client side
zc_events.post_no_wait('add', data={'x': 1, 'y': 1})
```

### Wait for a response

```python
# Client side
response = zc_events.get('add', data={'x': 1, 'y': 1})
response.data  # {'answer': 2}
response.has_errors  # False
```


### Get errors

```python
# Client side
response = zc_events.get('add', data={'x': 1})
response.data  # None
response.has_errors  # True
response.errors  # [{ 'type': 'KeyError', 'message': 'y' }]
```

## Working Example

A working example can be found in the `examples` folder, and can be run via `docker-compose run client3` and `docker-compose run client2`.

# Installation

## Settings changes

In the `settings.py` file, add the following lines

```python
EVENTS_EXCHANGE = 'microservice-events' + ('' if STAGING_NAME == 'production' else '-{}'.format(STAGING_NAME))

events_exchange = Exchange(EVENTS_EXCHANGE, type='fanout')

CELERY_QUEUES = (
    # Add this line
    Queue(SERVICE_NAME + '-events', events_exchange),
)

CELERY_ROUTES = ('zc_events.routers.TaskRouter', )
```

## BROKER_URL

Make sure that the `BROKER_URL` either in ``.env.sample` or in `settings.py` if a default is defined there is in the following format. The old style of the trailing `//` won't work for development when emitting events.

```
BROKER_URL=amqp://guest:guest@rabbitmq:5672/%2F
```

## New requirements

Sending and receiving events requires the `pika` and `ujson` libraries to be installed via pip and added to the `requirements.txt` file.

## Set up service for listening to events

Create a file called `microservice_events.py` and place it somewhere like the `mp-slots-and-orders/slots_and_orders/tasks/` directory. For now this will be an empty file, but in the future this is where any events that this service listens to will go.

Next create a file called `microservice_events_listener.py` and place it in the same directory. This file will have the following contents (replacing `slots_and_orders` with the current project name)

```python
import logging
from slots_and_orders import celery_app as app
from . import microservice_events

@app.task(name='microservice.event')
def microservice_event(event_type, *args, **kwargs):
    if hasattr(microservice_events, event_type):
        logger.info('MICROSERVICE_EVENT::PROCESSED: Received [{}:{}] event for object ({}:{}) and user {}'.format(
            event_type, kwargs.get('task_id'), kwargs.get('resource_type'), kwargs.get('resource_id'), kwargs.get('user_id')))

        getattr(microservice_events, event_type)(*args, **kwargs)
    else:
        logger.info('MICROSERVICE_EVENT::IGNORED: Received [{}:{}] event for object ({}:{}) and user {}'.format(
            event_type, kwargs.get('task_id'), kwargs.get('resource_type'), kwargs.get('resource_id'), kwargs.get('user_id')))

```

Note: Feel free to use explicit imports here, just make sure you're importing the correct things. They are specified as relative here to be as generic as possible.

Go back to `settings.py` and add the new event listener file to `CELERY_IMPORTS` which you may need to create if it doesn't already exist

```python
CELERY_IMPORTS = (
    'slots_and_orders.tasks.microservice_events_listener',
)
```

## How to configure a service to listen to events

In the `proj/proj/__init__.py` file, import and instantiate the `EventClient` from `zc_events`. This will serve as a singleton for all event requests and holds a Redis connection pool and RabbitMQ connection pool open for events. This is a good time to add the Celery import in here as well and make sure all parts of the project import celery from here.

```python
from __future__ import absolute_import, unicode_literals
from .celery import app as celery_app

from zc_events import EventClient


event_client = EventClient()
__all__ = ['celery_app']
```

When you need to make a service-to-service request, you can now do something similar to this:

```python
from slots_and_orders import event_client

order = event_client.get_remote_resource('Order', '23131024')
print 'Order name: {}'.format(order.name)
```

## Util functions

You may need to save or read data from S3 as part of your event processing. In such cases, refer to `zc_events.aws.py` module. It contains a few helper functions to do common routines. 
