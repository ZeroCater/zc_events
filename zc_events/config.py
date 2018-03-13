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
import uuid
try:
    from django.conf import settings as django_settings
except ImportError:
    django_settings = None


logger = logging.getLogger(__name__)


class _LazySettings:
    """A lazy way to retrieve settings.

    This class makes it possible to import settings, but they are not evaluated until they are needed.

    Note:
        If django is installed, it uses django's settings. If not, the it gets the settings from
        whatever file is imported from the `ZC_EVENTS_SETTINGS` env. variable.
    """

    def __init__(self):
        self._settings = None

    def __getattr__(self, name):
        if not self._settings:
            if django_settings:
                logger.debug('zc_events is using django settings')
                self._settings = django_settings
            else:
                logger.debug('zc_events could not use django settings, using ZC_EVENTS_SETTINGS')
                import_path = os.environ.get('ZC_EVENTS_SETTINGS')
                try:
                    self._settings = importlib.import_module(import_path)
                except Exception as e:
                    logger.exception(
                        'zc_events could not import settings. '
                        'Did you forget to set ZC_EVENTS_SETTINGS? path={import_path}'.format(
                            import_path=import_path
                        )
                    )
                    raise e
        if hasattr(self._settings, name):
            return getattr(self._settings, name)
        else:
            raise AttributeError('zc_events could not find {name} in settings.'.format(name=name))


settings = _LazySettings()
