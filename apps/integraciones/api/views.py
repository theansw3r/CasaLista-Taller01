from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integraciones.api.serializers import CondicionesClimaSerializer
from apps.integraciones.infraestructura.factories import crear_proveedor_clima
from apps.integraciones.services import ConsultaAliadoService, ConsultaClimaService


class ClimaView(APIView):
    """GET /api/v1/integraciones/clima/ -> clima actual de Medellin."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        servicio = ConsultaClimaService(crear_proveedor_clima())
        return Response(CondicionesClimaSerializer(servicio.consultar()).data)


class AliadoView(APIView):
    """GET /api/v1/integraciones/aliado/ -> 503 hasta tener el contrato."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(ConsultaAliadoService().consultar())
