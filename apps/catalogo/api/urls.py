"""Rutas del modulo Catalogo (prefijo /api/v1/catalogo/)."""

from django.urls import path

from apps.catalogo.api.views import BuscarProfesionalesView, ServiciosDelProfesionalView

app_name = "catalogo"

urlpatterns = [
    path("profesionales/", BuscarProfesionalesView.as_view(), name="profesionales"),
    path(
        "profesionales/<int:profesional_id>/servicios/",
        ServiciosDelProfesionalView.as_view(),
        name="servicios-del-profesional",
    ),
]
