from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.i18n import JavaScriptCatalog
from apps.integraciones.views import ClimaView, AliadoView

from apps.comun.api.views import IndiceView, SaludView

API = "api/v1/"

urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="index.html",
            extra_context={"url_pagos": settings.URL_PAGOS},
        ),
        name="inicio",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("api/v1/integraciones/clima/", ClimaView.as_view()),
    path("api/v1/integraciones/aliado/", AliadoView.as_view()),
    path("admin/", admin.site.urls),
    path("api/", IndiceView.as_view(), name="indice"),
    path(f"{API}cuentas/", include("apps.cuentas.api.urls")),
    path(f"{API}catalogo/", include("apps.catalogo.api.urls")),
    path(f"{API}reservas/", include("apps.reservas.api.urls")),
    # Legacy: sigue funcionando mientras dure la migracion a /api/v2/pagos/.
    path(f"{API}pagos/", include("apps.pagos.api.urls")),
    path(f"{API}salud/", SaludView.as_view(), name="salud"),
    path("interno/", include("apps.reservas.api.urls_internas")),
]
