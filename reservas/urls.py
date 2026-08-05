from django.urls import path

from reservas.views import CrearReservaView

app_name = "reservas"

urlpatterns = [
    path("reservas/", CrearReservaView.as_view(), name="crear"),
]
