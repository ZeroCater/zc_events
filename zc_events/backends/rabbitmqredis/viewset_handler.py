import ujson as json

from zc_events.exceptions import ImproperlyConfigured


def is_compatible(func):
    """Determine if the function is a compatible view or viewset

    Args:
        func: the function in question.

    Returns:
        bool: If the function is compatible return True
    """
    return hasattr(func, 'view_class') or hasattr(func, 'as_view')


def handle(func, data, relationship_viewset=None):
    """Handles dispatching the event to the view/viewset.

    The `data` arg is the most important because it determines a lot of what goes on. The only
    key that is required is the method key. Here are all keys:
        'data': The normal response body type of data, and ends up in response.body.
        'response_key': The key used to respond with.
        '_backend': {
            'method': A GET/POST/DELETE http verb
        }
        'headers': {
            'pk': The primary key, used to determine if it is a detail route or not
            'roles': The role assigned in the JWT in the request header
            'user_id': The user making the request, part of the JWT
            'http_host': unknown usage
            'query_string': unknown usage
            'relationship': unknown usage
            'related_resource': unknown usage
        }

    Note:
        This is setup with a JSONAPI, DRF and JWT configuration in mind. It is not
        expected to work with regular django class based views.

    Args:
        func: The view/viewset to dispatch to.
        data: A dictionary like object holding the keys documented above.
        relationship_viewset: Optional viewset for relations.
    """
    prepared_data = _prepare_data(data)
    django_request = _create_request(prepared_data)
    handler, handler_kwargs = _make_request_handler(prepared_data, func, relationship_viewset)
    django_response = handler(django_request, **handler_kwargs)
    return _serialize_response(django_response)


def _prepare_data(data):
    body = data.get('data')
    method = data.get('_backend').get('method')
    headers = data.get('headers', {})
    roles = headers.get('roles')
    user_id = headers.get('user_id')
    http_host = headers.get('http_host')
    query_string = headers.get('query_string')
    response_key = data.get('response_key')
    pk = headers.get('pk')
    relationship = headers.get('relationship')
    related_resource = headers.get('related_resource')

    return {
        'roles': roles,
        'user_id': user_id,
        'body': body,
        'method': method,
        'http_host': http_host,
        'query_string': query_string,
        'response_key': response_key,
        'pk': pk,
        'relationship': relationship,
        'related_resource': related_resource
    }


def _create_request(event):
    from zc_events.django_request import create_django_request_object
    return create_django_request_object(
        roles=event.get('roles'),
        query_string=event.get('query_string'),
        method=event.get('method'),
        user_id=event.get('user_id', None),
        body=event.get('body', None),
        http_host=event.get('http_host', None)
    )


def _make_request_handler(event, func, relationship_viewset):
    # use ViewSetMixin because that is where the magic happens...
    # https://github.com/encode/django-rest-framework/blob/73203e6b5920dcbe78e3309b7bf2803eb56db536/rest_framework/viewsets.py#L35
    from rest_framework.viewsets import ViewSetMixin
    if issubclass(func, ViewSetMixin):
        viewset = func
        view = None
    else:
        viewset = None
        view = func

    if not any([view, viewset, relationship_viewset]):
        raise ImproperlyConfigured('handle_request_event must be passed either a view or viewset')

    pk = event.get('pk', None)
    relationship = event.get('relationship', None)
    related_resource = event.get('related_resource', None)

    handler_kwargs = {}
    if view:
        handler = view.as_view()
    elif pk:
        handler_kwargs['pk'] = pk
        if relationship:
            # Relationship views expect this kwarg as 'related_field'. See https://goo.gl/WW4ePd
            handler_kwargs['related_field'] = relationship
            handler = relationship_viewset.as_view()
        elif related_resource:
            handler = viewset.as_view({'get': related_resource})
            handler_kwargs['related_resource'] = related_resource
        else:
            handler = _get_handler_for_viewset(viewset, is_detail=True)
    else:
        handler = _get_handler_for_viewset(viewset, is_detail=False)
    return handler, handler_kwargs


def _get_handler_for_viewset(viewset, is_detail):
    if is_detail:
        methods = [
            ('get', 'retrieve'),
            ('put', 'update'),
            ('patch', 'partial_update'),
            ('delete', 'destroy'),
        ]
    else:
        methods = [
            ('get', 'list'),
            ('post', 'create'),
        ]
    actions = {}
    for method, action in methods:
        if hasattr(viewset, action):
            actions[method] = action

    return viewset.as_view(actions)


def _serialize_response(response):
    serialized = {
        'data': None,
        'has_errors': False,
        'errors': []
    }
    if response.status_code >= 400:
        serialized['has_errors'] = True
        serialized['errors'] = response.data
    else:
        serialized['data'] = json.loads(response.rendered_content)
    return serialized
