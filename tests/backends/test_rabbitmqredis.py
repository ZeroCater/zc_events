import mock
import pytest
import ujson as json
import uuid
from zc_events.backends import rabbitmq_dispatch_task, RabbitMqFanoutBackend
from zc_events.backends.rabbitmqredis.client import _format_data, _place_on_queue, _get_response


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


class TestFormatData:

    def test_returns_body_task_id_and_task_name(self):
        data = {'id': 'abc-123', 'response_key': 'rk-456', 'foo': 'bar'}
        body, task_id, task_name = _format_data(data, 'GET', 'some_key')

        assert task_id == 'abc-123'
        assert task_name == 'microservice.event'

    def test_body_is_three_tuple(self):
        data = {'id': 'abc-123', 'response_key': 'rk-456', 'foo': 'bar'}
        body, task_id, task_name = _format_data(data, 'POST', 'some_key')

        assert isinstance(body, tuple)
        assert len(body) == 3

        args, kwargs, embed = body
        assert isinstance(args, list)
        assert len(args) == 2
        assert args[0] == 'some_key'
        assert args[1] is data
        assert kwargs == {}
        assert embed == {'callbacks': None, 'errbacks': None, 'chain': None, 'chord': None}

    def test_sets_backend_metadata_on_data(self):
        data = {'id': 'abc-123', 'response_key': 'rk-456'}
        _format_data(data, 'PUT', 'my_key')

        assert data['_backend'] == {
            'type': 'rabbitmqfanout',
            'method': 'PUT',
            'key': 'my_key'
        }

    def test_body_is_json_serializable(self):
        data = {'id': 'abc-123', 'response_key': 'rk-456'}
        body, _, _ = _format_data(data, 'GET', 'key')
        serialized = json.dumps(body)
        deserialized = json.loads(serialized)
        assert isinstance(deserialized, list)
        assert len(deserialized) == 3


class TestPlaceOnQueue:

    def test_publishes_with_protocol2_headers(self):
        mock_pool = mock.MagicMock()
        mock_channel = mock_pool.acquire.return_value.__enter__.return_value.channel

        _place_on_queue(
            mock_pool,
            'test-exchange',
            '',
            9,
            '[[\"key\", {}], {}, {}]',
            'task-id-123',
            'microservice.event',
            "['key', {}]"
        )

        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        properties = call_args[0][3]

        assert properties.content_type == 'application/json'
        assert properties.content_encoding == 'utf-8'
        assert properties.priority == 9
        assert properties.correlation_id == 'task-id-123'

        headers = properties.headers
        assert headers['lang'] == 'py'
        assert headers['task'] == 'microservice.event'
        assert headers['id'] == 'task-id-123'
        assert headers['root_id'] == 'task-id-123'
        assert headers['parent_id'] is None
        assert headers['group'] is None
        assert headers['retries'] == 0
        assert headers['timelimit'] == [None, None]
        assert headers['origin'] == ''
        assert headers['argsrepr'] == "['key', {}]"
        assert headers['kwargsrepr'] == '{}'


class TestEnqueueIntegration:

    def test_post_no_wait_sends_protocol2_message(self):
        mock_pool = mock.MagicMock()
        mock_channel = mock_pool.acquire.return_value.__enter__.return_value.channel

        backend = RabbitMqFanoutBackend(redis_client=mock.MagicMock(), pika_pool=mock_pool)
        data = {'id': 'test-id', 'response_key': 'rk-1', 'payload': 'hello'}
        backend.post_no_wait('events/test', data)

        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args

        # Verify body is the 3-tuple format (serialized as JSON array)
        published_body = json.loads(call_args[0][2])
        assert isinstance(published_body, list)
        assert len(published_body) == 3
        args, kwargs, embed = published_body
        assert args[0] == 'events/test'
        assert args[1]['id'] == 'test-id'
        assert kwargs == {}
        assert embed == {'callbacks': None, 'errbacks': None, 'chain': None, 'chord': None}

        # Verify headers
        properties = call_args[0][3]
        assert properties.correlation_id == 'test-id'
        assert properties.headers['task'] == 'microservice.event'
        assert properties.headers['id'] == 'test-id'
