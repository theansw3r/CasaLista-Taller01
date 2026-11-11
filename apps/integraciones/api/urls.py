from django.urls import path

from apps.integraciones.api.views import AliadoView, ClimaView

app_name = "integraciones"

urlpatterns = [
    path("clima/", ClimaView.as_view(), name="clima"),
    path("aliado/", AliadoView.as_view(), name="aliado"),
]
