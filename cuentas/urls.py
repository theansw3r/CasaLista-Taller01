from django.urls import include, path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("registro/", views.registro, name="registro"),
]
