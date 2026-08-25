from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.cuentas.api.views import (
    PerfilView,
    RegistrarClienteView,
    RegistrarProfesionalView,
)

app_name = "cuentas"

urlpatterns = [
    path("registro/cliente/", RegistrarClienteView.as_view(), name="registro-cliente"),
    path(
        "registro/profesional/",
        RegistrarProfesionalView.as_view(),
        name="registro-profesional",
    ),
    path("token/", TokenObtainPairView.as_view(), name="token"),
    path("token/refrescar/", TokenRefreshView.as_view(), name="token-refrescar"),
    path("perfil/", PerfilView.as_view(), name="perfil"),
]
