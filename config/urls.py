"""Project URL configuration: admin panel, OpenAPI schema, interactive docs, and API routes."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # OpenAPI schema & docs
    # JSON by default; add ?format=yaml to get a YAML schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Application API
    path("api/", include("shop.urls")),

    # Convenience: redirect project root to interactive API docs
    path("", RedirectView.as_view(pattern_name="swagger-ui", permanent=False)),
]
# Serve media files in development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
