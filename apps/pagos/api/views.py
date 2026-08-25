from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pagos.api.serializers import PagoSerializer, ProcesarPagoSerializer
from apps.pagos.services import ConsultaPagosService, PagoService


class ProcesarPagoView(APIView):

    permission_classes = [IsAuthenticated]
    servicio = PagoService

    def post(self, request):
        entrada = ProcesarPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pago = self.servicio().procesar(entrada.a_comando(request.user.pk))
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)


class PagoDetalleView(APIView):

    permission_classes = [IsAuthenticated]
    servicio = ConsultaPagosService

    def get(self, request, pago_id: int):
        pago = self.servicio().detalle_de(request.user.pk, pago_id)
        return Response(PagoSerializer(pago).data, status=status.HTTP_200_OK)
