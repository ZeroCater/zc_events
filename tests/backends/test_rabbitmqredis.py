import pytest
import uuid
from zc_events.backends import rabbitmq_dispatch_task, RabbitMqFanoutBackend
from zc_events.backends.rabbitmqredis import _get_response


class TestDispatchingEvents:
    """Test dispatching a request to the appropriate function and responding.

    Dispatching happens on the server side.

    Note:
        This might be generic enough to test any other backend we implement, with some modification.
    """

    def _setup(self):
        self.response_key = str(uuid.uuid4)
        self.request_data = {
            'response_key': self.response_key,
            'id': '456',
            'data': {
                'x': 1, 'y': 2
            }
        }
        self.redis_client = RabbitMqFanoutBackend()._redis_client
        self.redis_client.flushdb()

    def _get_response(self):
        return _get_response(self.redis_client, self.response_key)

    def test_valid_response(self):
        self._setup()
        responded, key_found = rabbitmq_dispatch_task('add', self.request_data)
        response = self._get_response()
        assert responded is True
        assert key_found is True
        assert response.data == 3
        assert response.has_errors is False
        assert response.errors == []

    def test_exception_thrown(self):
        self._setup()
        del self.request_data['data']['y']
        responded, key_found = rabbitmq_dispatch_task('add', self.request_data)
        response = self._get_response()
        assert responded is True
        assert key_found is True
        assert response.data is None
        assert response.has_errors is True
        assert 'trace' in response.errors[0]
        # It returns a stack trace on error, but it's tough to match the exact string.
        del response.errors[0]['trace']
        assert response.errors == [{'type': 'KeyError', 'message': "'y'"}]

    def test_no_response_key(self):
        self._setup()
        self.request_data['response_key'] = None
        responded, key_found = rabbitmq_dispatch_task('add', self.request_data)
        assert responded is False
        assert key_found is True

    def test_no_method_mapped(self):
        self._setup()
        responded, key_found = rabbitmq_dispatch_task('subtract', self.request_data)
        assert responded is False
        assert key_found is False
