import ujson as json
from zc_events.request import wrap_resource_from_response


def wrap_response(json_data):
    """Transforms a jsonapi response into an object that is easier to work with.

    It takes data such as:
        {
            'data': {
                'type': 'AddView', 'id': '-1',
                'attributes': {'answer': 3, 'method': 'POST'}
            }
        }

    And returns an object with many of the top level keys, for instance:

        assert obj.type == 'AddView'
        assert obj.id == '-1'
        assert obj.answer == 3
        assert obj.method == 'POST'

    Args:
        json_data: A dict of data to be wrapped in an object.

    Return:
        A wrapped object with many of the keys surfaced to the top.
    """
    body = {'body': json.dumps(json_data)}
    return wrap_resource_from_response(body)
