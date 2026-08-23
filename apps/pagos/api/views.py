"""
Capa de presentacion del modulo Pagos.

Codigos que devuelve este modulo:

    201  el pago se aprobo y la reserva quedo CONFIRMADA
    400  el cuerpo es invalido (medio de pago desconocido, id ausente)
    403  la reserva es de otro cliente
    404  la reserva o el pago no existen
    409  la reserva ya estaba pagada, no admite pago, o la pasarela rechazo
    502  la pasarela no respondio
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pagos.api.serializers import PagoSerializer, ProcesarPagoSerializer
from apps.pagos.services import ConsultaPagosService, PagoService


class ProcesarPagoView(APIView):
    """POST /api/v1/pagos/ -> cobra la reserva y la confirma (RN-03)."""

    permission_classes = [IsAuthenticated]
    servicio = PagoService

    @extend_schema(
        summary="Pagar una reserva (Factory de pasarelas)",
        request=ProcesarPagoSerializer,
        responses={201: PagoSerializer},
        tags=["pagos"],
    )
    def post(self, request):
        entrada = ProcesarPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pago = self.servicio().procesar(entrada.a_comando(request.user.pk))
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)


class PagoDetalleView(APIView):
    """GET /api/v1/pagos/<id>/ -> 200 | 403 | 404."""

    permission_classes = [IsAuthenticated]
    servicio = ConsultaPagosService

    @extend_schema(
        summary="Detalle de un pago propio",
        responses={200: PagoSerializer},
        tags=["pagos"],
    )
    def get(self, request, pago_id: int):
        pago = self.servicio().detalle_de(request.user.pk, pago_id)
        return Response(PagoSerializer(pago).data, status=status.HTTP_200_OK)
