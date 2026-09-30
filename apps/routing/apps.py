"""
App configuration for the routing app.
"""
from django.apps import AppConfig


class RoutingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.routing'
    verbose_name = 'Routing'
