import logging
import ujson as json
import traceback
import six
from zc_events.config import settings
from zc_events.request import Request
from zc_events.backends.rabbitmqredis.common import format_exception_response
from zc_events.backends.rabbitmqredis import viewset_handler

if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)


def respond(redis_client, response_key, data):
    """Low level responder for redis. It is intended to be used
    by the backend_client.respond method and not directly by the end user.

    Args:
        redis_client: A redis client
        response_key: The response key in which push the response to.
        data: A dictionary like object to put into the redis response (json.dumps first)
    """
    result = redis_client.rpush(response_key, json.dumps(data))
    redis_client.expire(response_key, 60)
    return result


def _handle_regular_func(func, data):
    request = Request(data)
    return {
        'data': func(request),
        'has_errors': False,
        'errors': []
    }


def _get_job_info(name):
    val = settings.JOB_MAPPING.get(name)
    if isinstance(val, Mapping):
        return val.get('func'), val.get('relationship_viewset')
    return val, None


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
    func, relationship_viewset = _get_job_info(name)
    if not func:
        logger.info('zc_events did not find name={name}'.format(name=name))
        return (False, False)
    else:
        try:
            if viewset_handler.is_compatible(func):
                response = viewset_handler.handle(
                    func,
                    data,
                    relationship_viewset=relationship_viewset
                )
            else:
                response = _handle_regular_func(func, data)
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
            response = format_exception_response(ex_type, msg, trace)
        backend = settings.RPC_BACKEND
        logger.info('zc_events finished name={name} data={data} response={response}'.format(
            name=name, data=data, response=response))
        return (backend.respond(data.get('response_key'), response), True)
