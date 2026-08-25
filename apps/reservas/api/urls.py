from django.urls import path

from apps.reservas.api.views import (
    CancelarReservaView,
    DisponibilidadView,
    MiAgendaView,
    ReservaDetalleView,
    ReservasRecibidasView,
    ReservasView,
)

app_name = "reservas"

urlpatterns = [
    path("disponibilidad/", DisponibilidadView.as_view(), name="disponibilidad"),
    path("mi-agenda/", MiAgendaView.as_view(), name="mi-agenda"),
    path("recibidas/", ReservasRecibidasView.as_view(), name="recibidas"),
    path("", ReservasView.as_view(), name="reservas"),
    path("<int:reserva_id>/", ReservaDetalleView.as_view(), name="detalle"),
    path(
        "<int:reserva_id>/cancelacion/",
        CancelarReservaView.as_view(),
        name="cancelacion",
    ),
]
