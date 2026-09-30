from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.comun.api.views import IndiceView, SaludView

API = "api/v1/"

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="inicio"),
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
