"""Vistas transversales que no pertenecen a ningun modulo del dominio."""

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.api.serializers import SaludSerializer


class SaludView(APIView):
    """GET /api/v1/salud/ -> estado de la instancia.

    Lo consulta el balanceador que esta delante del Gateway para decidir si
    esta instancia sigue recibiendo trafico. Por eso responde 503 (y no 500)
    cuando la base de datos no contesta: 503 le dice al balanceador "sacame
    del pool", no "hay un bug".
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        summary="Estado de la instancia",
        responses={200: SaludSerializer, 503: SaludSerializer},
        tags=["operacion"],
    )
    def get(self, request):
        base_de_datos_viva = self._base_de_datos_responde()
        cuerpo = {
            "servicio": "casalista-api",
            "version": "1.0.0",
            "base_de_datos": "ok" if base_de_datos_viva else "sin-conexion",
            "id_peticion": getattr(request, "id_peticion", None),
        }
        codigo = (
            status.HTTP_200_OK
            if base_de_datos_viva
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(cuerpo, status=codigo)

    @staticmethod
    def _base_de_datos_responde() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001 - cualquier fallo aqui significa "no viva"
            return False
