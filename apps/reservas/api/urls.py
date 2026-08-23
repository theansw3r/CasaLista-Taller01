"""Rutas del modulo Agenda y Reservas (prefijo /api/v1/reservas/)."""

from django.urls import path

from apps.reservas.api.views import (
    CancelarReservaView,
    DisponibilidadView,
    ReservaDetalleView,
    ReservasView,
)

app_name = "reservas"

urlpatterns = [
    # Las rutas literales van antes que las que capturan un id, para que un
    # cambio futuro en los convertidores no las deje inalcanzables.
    path("disponibilidad/", DisponibilidadView.as_view(), name="disponibilidad"),
    path("", ReservasView.as_view(), name="reservas"),
    path("<int:reserva_id>/", ReservaDetalleView.as_view(), name="detalle"),
    path(
        "<int:reserva_id>/cancelacion/",
        CancelarReservaView.as_view(),
        name="cancelacion",
    ),
]
