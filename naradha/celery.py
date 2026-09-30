"""
Celery configuration for the NARADHA project.

Usage:
  celery -A naradha worker -l info
  celery -A naradha beat -l info
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'naradha.settings')

app = Celery('naradha')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Small task for verifying the worker wiring."""
    print(f'Request: {self.request!r}')
