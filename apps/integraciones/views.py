from django.core.cache import cache
from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integraciones.adaptadores import OpenMeteoAdapter
from apps.integraciones.services import ConsultaClimaService


class ClimaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        dato = cache.get("clima-medellin-v1")
        if dato is None:
            dato = ConsultaClimaService(OpenMeteoAdapter()).consultar()
            cache.set("clima-medellin-v1", dato, timeout=300)
        return Response(dato)


class AliadoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # No se inventa ni contrato ni datos de otro equipo.
        return Response({"error": {"codigo": "ALIADO-PENDIENTE", "mensaje": _(
            "Integración pendiente: falta identificar el equipo aliado y su contrato de API."
        )}}, status=503)
