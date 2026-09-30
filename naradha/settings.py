"""
Django settings for the NARADHA project.

Civic complaint management platform with AI-assisted evidence
verification, SLA tracking, and real-time messaging.

Environment-driven configuration:
  - Copy .env.example to .env and adjust values, or export the
    variables in your shell / hosting platform.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-dev-key-change-me-in-production'),
    ALLOWED_HOSTS=(list, ['*']),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'django_filters',
]

LOCAL_APPS = [
    'apps.users',
    'apps.complaints',
    'apps.ai_services',
    'apps.verification',
    'apps.routing',
    'apps.fieldwork',
    'apps.messaging',
    'apps.dashboard',
    'apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'naradha.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'naradha.wsgi.application'
ASGI_APPLICATION = 'naradha.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
if os.environ.get('DATABASE_URL'):
    _db = env.db_url_config(os.environ['DATABASE_URL'])
    # django-environ's legacy 'file:' scheme maps to SQLite
    if _db['ENGINE'].endswith('.file') or _db['ENGINE'] == 'file':
        _db['ENGINE'] = 'django.db.backends.sqlite3'
    if _db['ENGINE'] == 'django.db.backends.sqlite3' and not os.path.isabs(str(_db['NAME'])):
        _db['NAME'] = str(BASE_DIR / str(_db['NAME']))
    DATABASES = {'default': _db}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }
_sqlite_name = DATABASES['default'].get('NAME')
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3' and _sqlite_name:
    # Ensure the parent directory of the SQLite file exists
    _db_dir = os.path.dirname(str(_sqlite_name))
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
    # WAL mode gives better concurrency for the dev setup
    DATABASES['default'].setdefault('OPTIONS', {'init_command': 'PRAGMA journal_mode=WAL;'})

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', default='Asia/Kolkata')
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Non-manifest storage: serves static files with gzip compression but
        # never raises "Missing staticfiles manifest entry" (HTTP 500) when
        # `python manage.py collectstatic` has not been run yet.
        # Swap to whitenoise.storage.CompressedManifestStaticFilesStorage for
        # cache-busting hashed filenames once your deployment pipeline runs
        # collectstatic on every release.
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'
        if not DEBUG else
        'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload limits (10 MB default)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_MINUTES', default=60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:3000'])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ---------------------------------------------------------------------------
# Channels (WebSockets)
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': env(
            'CHANNEL_BACKEND',
            default='channels.layers.InMemoryChannelLayer'
        ),
    }
}
# For production use Redis:
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {'hosts': [env('REDIS_URL', default='redis://127.0.0.1:6379/0')]},
#     }
# }

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='memory://')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='cache+memory://')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True

# Periodic beat schedule (SLA checks)
CELERY_BEAT_SCHEDULE = {
    'check-sla-breaches': {
        'task': 'apps.ai_services.tasks.check_sla_breaches',
        'schedule': 60.0 * 30,  # every 30 minutes
    },
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@naradha.example')

# ---------------------------------------------------------------------------
# NARADHA application settings
# ---------------------------------------------------------------------------
NARADHA = {
    # AI must score a complaint's evidence at least this high (0-100)
    'AI_CONFIDENCE_THRESHOLD': env.int('NARADHA_AI_CONFIDENCE_THRESHOLD', default=70),
    # Priority score (1-10) thresholds that map to priority levels
    'PRIORITY_THRESHOLDS': {
        'CRITICAL': env.int('NARADHA_PRIORITY_CRITICAL', default=9),
        'HIGH': env.int('NARADHA_PRIORITY_HIGH', default=7),
        'MEDIUM': env.int('NARADHA_PRIORITY_MEDIUM', default=4),
    },
    # Days before SLA breach after a commitment is published
    'DEFAULT_SLA_DAYS': env.int('NARADHA_DEFAULT_SLA_DAYS', default=14),
    # Max uploaded proof size in MB
    'MAX_PROOF_SIZE_MB': env.int('NARADHA_MAX_PROOF_SIZE_MB', default=10),
    # Enable/disable AI processing pipeline
    'AI_ENABLED': env.bool('NARADHA_AI_ENABLED', default=True),
}

# ---------------------------------------------------------------------------
# Security (production hardening when DEBUG=False)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
