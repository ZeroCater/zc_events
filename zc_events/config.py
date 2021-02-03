"""How zc_events retrieves and gets settings.

This is a lazily evaluated settings module that first tries to read
from django settings, but if it is not available, reads from whatever
file is imported via the `ZC_EVENTS_SETTINGS` environment variable.

Example:
    export ZC_EVENTS_SETTINGS=some.settings

    In this example, their is a python module called `some` with a file called
    `settings.py` which the settings will be loaded from.
"""
import logging
import importlib
import os

try:
    from django.conf import settings as django_settings
except ImportError:
    django_settings = None


logger = logging.getLogger(__name__)


class _LazySettings(object):
    """A lazy way to retrieve settings.

    This class makes it possible to import settings, but they are not evaluated until they are needed.

    Note:
        If `ZC_EVENTS_SETTINGS` is set then it uses that, if not it will try to use django's settings.
    """

    def __init__(self):
        self._settings = None

    def __getattr__(self, name):
        if not self._settings:
            import_path = os.environ.get('ZC_EVENTS_SETTINGS')
            if import_path:
                logger.debug('zc_events is using ZC_EVENTS_SETTINGS path={path}'.format(path=import_path))
                try:
                    self._settings = importlib.import_module(import_path)
                except ImportError as e:
                    logger.exception(
                        'zc_events could not import settings. '
                        'The path was not valid. path={import_path}'.format(
                            import_path=import_path
                        )
                    )
                    raise e
            elif django_settings:
                logger.debug('zc_events is using django settings')
                self._settings = django_settings
            else:
                raise RuntimeError('zc_events could not find valid settings. Please set ZC_EVENTS_SETTINGS')
        if hasattr(self._settings, name):
            return getattr(self._settings, name)
        else:
            raise AttributeError('zc_events could not find {name} in settings.'.format(name=name))


settings = _LazySettings()
