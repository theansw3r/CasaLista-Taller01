"""
Tabla de rutas raiz.

Toda la API cuelga de /api/v1/ y, dentro de ese prefijo, cada modulo del
dominio tiene su propio segmento (/cuentas/, /catalogo/, /reservas/, /pagos/).

Esto no es cosmetico: es la condicion para que un API Gateway pueda enrutar
por prefijo hacia servicios distintos el dia que un modulo se extraiga. Ver
docs/wiki/05-API-Gateway.md.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.comun.api.views import SaludView

API = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    # --- Modulos del dominio -----------------------------------------------
    path(f"{API}cuentas/", include("apps.cuentas.api.urls")),
    path(f"{API}catalogo/", include("apps.catalogo.api.urls")),
    path(f"{API}reservas/", include("apps.reservas.api.urls")),
    path(f"{API}pagos/", include("apps.pagos.api.urls")),
    # --- Operacion ----------------------------------------------------------
    # El Gateway y el balanceador consultan este endpoint para decidir si la
    # instancia sigue en el pool.
    path(f"{API}salud/", SaludView.as_view(), name="salud"),
    # --- Contrato -----------------------------------------------------------
    # El Gateway importa este esquema OpenAPI para generar sus rutas, validar
    # las peticiones en el borde y publicar el portal de desarrolladores.
    path("api/schema/", SpectacularAPIView.as_view(), name="esquema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="esquema"),
        name="documentacion",
    ),
]
