from django.urls import path

from apps.catalogo.api.views import (
    BuscarProfesionalesView,
    MisServiciosView,
    ServiciosDelProfesionalView,
)

app_name = "catalogo"

urlpatterns = [
    path("profesionales/", BuscarProfesionalesView.as_view(), name="profesionales"),
    path("mis-servicios/", MisServiciosView.as_view(), name="mis-servicios"),
    path(
        "profesionales/<int:profesional_id>/servicios/",
        ServiciosDelProfesionalView.as_view(),
        name="servicios-del-profesional",
    ),
]
