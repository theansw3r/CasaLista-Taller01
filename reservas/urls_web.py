from django.urls import path

from .views_web import InicioView, MisReservasListView

app_name = "portal"

urlpatterns = [
    path("", InicioView.as_view(), name="inicio"),
    path("mis-reservas/", MisReservasListView.as_view(), name="mis-reservas"),
]
