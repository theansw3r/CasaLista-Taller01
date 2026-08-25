from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.services import IndiceService, SaludService


class IndiceView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []
    servicio = IndiceService

    def get(self, request):
        return Response(self.servicio().describir(), status=status.HTTP_200_OK)


class SaludView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []
    servicio = SaludService

    def get(self, request):
        reporte, viva = self.servicio().estado()
        reporte["id_peticion"] = getattr(request, "id_peticion", None)
        codigo = (
            status.HTTP_200_OK if viva else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(reporte, status=codigo)
