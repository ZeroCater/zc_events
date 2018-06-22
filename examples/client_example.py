import time
from zc_events.client import EventClient
from zc_events.backends.rabbitmqredis import jsonapi

time.sleep(10)  # Allow rabbitmq/redis/worker to come up

c = EventClient()

# The easiest way to call a remote function
assert c.call('add', data={'x': 1, 'y': 1}).data == 2
assert c.get('add', data={'x': 1, 'y': 2}).data == 3
assert c.put('add', data={'x': 1, 'y': 4}).data == 5
assert c.post('add', data={'x': 21, 'y': 2}).data == 23
assert c.delete('add', data={'x': 10, 'y': 20}).data == 30

assert c.call_no_wait('add', data={'x': 1, 'y': 1}) is None
assert c.put_no_wait('add', data={'x': 1, 'y': 2}) is None
assert c.post_no_wait('add', data={'x': 1, 'y': 2}) is None
assert c.delete_no_wait('add', data={'x': 1, 'y': 2}) is None

bad_response = c.get('add', data={'x': 1})
assert bad_response.has_errors is True
assert 'trace' in bad_response.errors[0]
# It returns a stack trace on error, but it's tough to match the exact string.
del bad_response.errors[0]['trace']
assert bad_response.errors == [{'type': 'KeyError', 'message': "'y'"}]
assert bad_response.data is None

good_response = c.get('add', data={'x': 1, 'y': 2})
assert good_response.has_errors is False
assert good_response.errors == []
assert good_response.data == 3

# Django Rest Framework integration (JSON API implementation)
drf_data = {'data': {'type': 'AddView', 'attributes': {'x': 1, 'y': 2}}}


def expected_data(method, pk='-1'):
    return {
        'data': {
            'type': 'AddView',
            'id': str(pk),
            'attributes': {'answer': 3, 'method': method}
        }
    }


assert c.call('add_drf', data=drf_data).data == expected_data('POST')
assert c.get('add_drf', data=drf_data).data == expected_data('GET')
assert c.post('add_drf', data=drf_data).data == expected_data('POST')
# Use the `pk` key on a header to go to a detail view
assert c.delete('add_drf', data=drf_data, headers={'pk': 3}).data == expected_data('DELETE', pk=3)
assert c.put('add_drf', data=drf_data, headers={'pk': 3}).data == expected_data('PUT', pk=3)
assert c.get('add_drf', data=drf_data, headers={'pk': 3}).data == expected_data('GET', pk=3)

bad_response = c.put('add_drf', data=drf_data)
expected_errors = [{'detail': 'Method "PUT" not allowed.', 'source': {'pointer': '/data'}, 'status': '405'}]
assert bad_response.has_errors is True
assert bad_response.errors == expected_errors
assert bad_response.data is None

# Now demonstrate wrapping a response into an easier to use object
response = c.call('add_drf', data=drf_data)
wrapped = jsonapi.wrap_response(response.data)
assert wrapped.id == '-1'
assert wrapped.answer == 3
assert wrapped.method == 'POST'
assert wrapped.type == 'AddView'

# Demonstrate how to work with query strings in a GET type of request to APIView
assert c.get('lookup_drf', headers={'query_string': 'x=1'}).data == {'data': 'y'}
# Do the same, but expect an error response from the server
assert c.get('lookup_drf', headers={'query_string': 'y=1'}).has_errors
