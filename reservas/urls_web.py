from django.urls import path

from .views_web import CrearReservaWebView, InicioView, MisReservasListView

app_name = "portal"

urlpatterns = [
    path("", InicioView.as_view(), name="inicio"),
    path("reservar/", CrearReservaWebView.as_view(), name="crear-reserva"),
    path("mis-reservas/", MisReservasListView.as_view(), name="mis-reservas"),
]
