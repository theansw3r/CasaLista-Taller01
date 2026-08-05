from django.urls import path

from .views import crear_reserva

app_name = "reservas"

urlpatterns = [
    path("reservas/", crear_reserva, name="crear-reserva"),
]
