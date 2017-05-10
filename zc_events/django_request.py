import ujson
import zlib

try:
    from zc_common.jwt_auth.utils import jwt_encode_handler
except ImportError:
    pass

from django.http import HttpRequest, QueryDict


def structure_response(status, data):
    """
    Compress a JSON object with zlib for inserting into redis.
    """
    return zlib.compress(ujson.dumps({
        'status': status,
        'body': data
    }))


def create_django_request_object(kwargs):
    """
    Create a Django HTTPRequest object with the appropriate attributes pulled
    from the event.
    """
    roles = kwargs.pop('roles')
    user_id = kwargs.pop('user_id', None)
    jwt_payload = {'roles': roles}
    if user_id:
        jwt_payload['id'] = user_id

    query_string = kwargs.pop('query_string')
    request = HttpRequest()
    request.GET = QueryDict(query_string)

    body = kwargs.pop('body', None)
    if body:
        request.read = lambda: ujson.dumps(body)

    request.encoding = 'utf-8'
    request.method = kwargs.pop('method').upper()
    request.META = {
        'HTTP_AUTHORIZATION': 'JWT {}'.format(jwt_encode_handler(jwt_payload)),
        'QUERY_STRING': query_string,
        'HTTP_HOST': kwargs.pop('http_host', 'local.zerocater.com'),
        'CONTENT_TYPE': 'application/vnd.api+json',
        'CONTENT_LENGTH': '99999',
    }

    return request, kwargs
