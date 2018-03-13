import time
from zc_events.client import EventClient

time.sleep(10)  # Allow rabbitmq/redis/worker to come up

c = EventClient()

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
