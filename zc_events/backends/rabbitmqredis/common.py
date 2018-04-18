def format_exception_response(exception_name, exception_msg, exception_trace):
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
