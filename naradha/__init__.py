"""
NARADHA - Civic complaint management platform.
Django project package.
"""
from .celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)
