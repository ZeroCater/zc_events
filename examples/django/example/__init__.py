from __future__ import absolute_import, unicode_literals
from .celery import app as celery_app

from zc_events import EventClient


event_client = EventClient()
__all__ = ['celery_app']
