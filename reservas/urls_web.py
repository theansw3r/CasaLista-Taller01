from django.urls import path

from .views_web import (
    CatalogoView,
    CrearReservaWebView,
    InicioView,
    MisReservasListView,
)

app_name = "portal"

urlpatterns = [
    path("", InicioView.as_view(), name="inicio"),
    path("reservar/", CatalogoView.as_view(), name="catalogo"),
    path(
        "reservar/<int:servicio_id>/",
        CrearReservaWebView.as_view(),
        name="crear-reserva",
    ),
    path("mis-reservas/", MisReservasListView.as_view(), name="mis-reservas"),
]
