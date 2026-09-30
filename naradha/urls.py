"""
Main URL configuration for the NARADHA project.

API structure:
  /api/auth/       - registration, profile, departments, jurisdictions
  /api/complaints/ - complaints REST API
  /api/ai/         - AI verification, scoring, routing services
  /api/fieldwork/  - field task management
  /api/dashboard/  - dashboards (public, citizen, official, minister, admin)
  /api/analytics/  - analytics and performance data
  /api/verifications/ - verification results
  /api/routing/    - routing logs & workloads

Frontend (server-rendered templates):
  /                - citizen portal home
  /complaints/...  - file / list / detail / track / verify pages
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # Frontend (server-rendered citizen portal)
    path('', include('apps.complaints.frontend_urls')),

    # REST API
    path('api/auth/', include('apps.users.urls')),
    path('api/complaints/', include('apps.complaints.urls')),
    path('api/ai/', include('apps.ai_services.urls')),
    path('api/fieldwork/', include('apps.fieldwork.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]

# Optional service URLs (kept out of the router for clarity)
try:
    from apps.verification.urls import urlpatterns as verification_urls  # noqa
    urlpatterns.append(path('api/verifications/', include('apps.verification.urls')))
except ImportError:
    pass

try:
    from apps.routing.urls import urlpatterns as routing_urls  # noqa
    urlpatterns.append(path('api/routing/', include('apps.routing.urls')))
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
