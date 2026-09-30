from django.urls import path

from apps.reservas.api.views import ConfirmarReservaInternaView

app_name = "interno"

# Rutas entre servicios. No van bajo /api/v1/ porque no son parte de la API
# publica: Nginx las bloquea y solo se llaman dentro de la red de Docker.
urlpatterns = [
    path(
        "reservas/<int:reserva_id>/confirmacion/",
        ConfirmarReservaInternaView.as_view(),
        name="confirmacion",
    ),
]
