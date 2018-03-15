import logging
import ujson as json
import pika
import pika_pool as pika_pool_lib
import redis
import traceback
from zc_events.config import settings
from zc_events.request import Request
from zc_events.responses import Response
from zc_events.exceptions import RequestTimeout

_DEFAULT_ROUTING_KEY = ''
_LOW_PRIORITY = 0
_HIGH_PRIORITY = 9


logger = logging.getLogger(__name__)


def _format_exception_response(exception_name, exception_msg, exception_trace):
    return {
        'data': None,
        'has_errors': True,
        'errors': [
            {
                'type': exception_name,
                'message': exception_msg,
                'trace': exception_trace
            }
        ]
    }


def dispatch_task(name, data):
    """Dispatch the task for processing on the server side.

    Example:
        @app.task('microservice.event')
        def listener(event_name, data):
            from zc_events.backends import dispatch_task
            return dispatch_task(event_name, data)


    Note:
        This function relies up `JOB_MAPPING` to be defined in your settings,
        which is a dict with the key corresponding to a name and the value being
        a function which will accept an `Request` paramater. If no name is found,
        nothing happens with the request.

        This function also needs the `RPC_BACKEND` setting to be instantiated
        so it can use the `respond` method.

    Args:
        name (str): The name of the function to be called.
        data (dict or None): The data to be used to populate the Request object.
    """
    logger.info('zc_events received name={name} data={data}'.format(name=name, data=data))
    request = Request(data)
    func = settings.JOB_MAPPING.get(name)
    if not func:
        logger.info('zc_events did not find name={name}'.format(name=name))
        return (False, False)
    else:
        try:
            response = {
                'data': func(request),
                'has_errors': False,
                'errors': []
            }
        except Exception as e:
            msg = str(e)
            ex_type = e.__class__.__name__
            trace = traceback.format_exc()
            logger.exception(
                'zc_events dispatched func threw an exception: name={name} data={data} '
                'exception={ex} message={msg} trace={trace}'.format(
                    name=name,
                    data=data,
                    ex=ex_type,
                    msg=msg,
                    trace=trace
                )
            )
            response = _format_exception_response(ex_type, msg, trace)
        backend = settings.RPC_BACKEND
        logger.info('zc_events finished name={name} data={data} response={response}'.format(
            name=name, data=data, response=response))
        return (backend.respond(request.response_key, response), True)


def _get_raw_response(redis_client, response_key):
    try:
        key_and_response = redis_client.blpop(response_key, 30)
        if key_and_response is None:
            raise RequestTimeout(detail='Timed out waiting for redis response')

        response = key_and_response[1]  # Index [0] is the response_key
        logger.debug('zc_events got response response_key={response_key} response={response}'.format(
            response_key=response_key,
            response=response
        ))
    except Exception as e:
        msg = str(e)
        ex_type = e.__class__.__name__
        trace = traceback.format_exc()
        logger.exception(
            'zc_events exception waiting for response response_key={response_key} '
            'exception={ex} message={msg} trace={trace}'.format(
                response_key=response_key,
                ex=ex_type,
                msg=msg,
                trace=trace
            )
        )
        response = json.dumps(_format_exception_response(ex_type, msg, trace))
    return response


def _get_response(redis_client, response_key):
    response = _get_raw_response(redis_client, response_key)
    json_response = json.loads(response)
    return Response(json_response)


def _respond(redis_client, response_key, data):
    result = redis_client.rpush(response_key, json.dumps(data))
    redis_client.expire(response_key, 60)
    return result


def _place_on_queue(pika_pool, events_exchange, routing_key, priority, event_body):
    event_queue_name = '{}-events'.format(settings.SERVICE_NAME)
    queue_arguments = {
        'x-max-priority': 10
    }
    response = None
    logger.debug(
        'zc_events placing on queue with the following '
        'events_exchange={events_exchange} routing_key={routing_key} '
        'event_body={event_body} priority={priority}'.format(
           events_exchange=events_exchange, routing_key=routing_key, event_body=event_body, priority=priority
        )
    )
    with pika_pool.acquire() as cxn:
        cxn.channel.queue_declare(queue=event_queue_name, durable=True, arguments=queue_arguments)
        response = cxn.channel.basic_publish(
            events_exchange,
            routing_key,
            event_body,
            pika.BasicProperties(
                content_type='application/json',
                content_encoding='utf-8',
                priority=priority
            )
        )

    if not response:
        raise EmitEventException("Message may have failed to deliver")
    return response


def _format_data(data, method, key):
    data['_backend'] = {
        'type': 'rabbitmqfanout',
        'method': method,
        'key': key
    }
    return {
        'task': 'microservice.event',
        'id': data['id'],
        'args': [key, data],
        'response_key': data['response_key']
    }


class RabbitMqFanoutBackend(object):
    """A backend implementation using Rabbitmq fanout strategy and redis for responses.

    The intent for this backend is to use a Rabbitmq fanout strategy, with redis for responding quickly.
    It is also required that the consumers of the events on Rabbitmq be using celery 3 or 4.

    Note:
        It is not intended to be used directly by developers, but instead set and instantiated
        through the RPC_BACKEND setting.

        All public methods are backend implementations for the corresponding methods on EventClient,
        except for the respond method.

    Args:
        redis_client (redis connection, (optional)): If this option is not provided, a redis connection
            is gotten by using the EVENTS_REDIS_URL in your settings, using db 0.
        pick_pool(pika_pool.QueuedPool, (optional)): The connection used by rabbitmq. If it is not provided,
            a connection is established using the BROKER_URL from settings.
    """

    def __init__(self, redis_client=None, pika_pool=None):
        self._redis_client = redis_client
        self._pika_pool = pika_pool
        self.__events_exchange = None

    @property
    def _redis_client(self):
        if not self.__redis_client:
            pool = redis.ConnectionPool().from_url(settings.EVENTS_REDIS_URL, db=0)
            self.__redis_client = redis.Redis(connection_pool=pool)
        return self.__redis_client

    @_redis_client.setter
    def _redis_client(self, value):
        self.__redis_client = value

    @property
    def _pika_pool(self):
        if not self.__pika_pool:
            pika_params = pika.URLParameters(settings.BROKER_URL)
            pika_params.socket_timeout = 5
            self.__pika_pool = pika_pool_lib.QueuedPool(
                create=lambda: pika.BlockingConnection(parameters=pika_params),
                max_size=10,
                max_overflow=10,
                timeout=10,
                recycle=3600,
                stale=45,
            )
        return self.__pika_pool

    @_pika_pool.setter
    def _pika_pool(self, value):
        self.__pika_pool = value

    @property
    def _events_exchange(self):
        if not self.__events_exchange:
            self.__events_exchange = settings.EVENTS_EXCHANGE
        return self.__events_exchange

    def call(self, key, data):
        return self.post(key, data)

    def call_no_wait(self, key, data):
        return self.post_no_wait(key, data)

    def get(self, key, data):
        data = _format_data(data, 'GET', key)
        return self._enqueue_with_waiting(data)

    def put(self, key, data):
        data = _format_data(data, 'PUT', key)
        return self._enqueue_with_waiting(data)

    def put_no_wait(self, key, data):
        data = _format_data(data, 'PUT', key)
        return self._enqueue_without_waiting(data)

    def post(self, key, data):
        data = _format_data(data, 'POST', key)
        return self._enqueue_with_waiting(data)

    def post_no_wait(self, key, data):
        data = _format_data(data, 'POST', key)
        return self._enqueue_without_waiting(data)

    def delete(self, key, data):
        data = _format_data(data, 'DELETE', key)
        return self._enqueue_with_waiting(data)

    def delete_no_wait(self, key, data):
        data = _format_data(data, 'DELETE', key)
        return self._enqueue_without_waiting(data)

    def _enqueue_without_waiting(self, data):
        _place_on_queue(
            self._pika_pool,
            self._events_exchange,
            _DEFAULT_ROUTING_KEY,
            _LOW_PRIORITY,
            json.dumps(data)
        )

    def _enqueue_with_waiting(self, data):
        _place_on_queue(
            self._pika_pool,
            self._events_exchange,
            _DEFAULT_ROUTING_KEY,
            _HIGH_PRIORITY,
            json.dumps(data)
        )
        return _get_response(self._redis_client, data['response_key'])

    def respond(self, response_key, data):
        """
        Respond to a request with the results.

        Args:
            response_key (str or None): If the response key is empty no response is done.
            data (dict): The fully formatted response to be sent to the client and passed to the Response object.

        Returns
            bool: True if responded, False if it did not.
        """
        logger.debug('zc_events responding with response_key={response_key} data={data}'.format(
            response_key=response_key, data=data
        ))
        if response_key:
            _respond(self._redis_client, response_key, data)
            return True
        return False
