from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cuentas.api.serializers import (
    ClienteSerializer,
    PerfilSerializer,
    ProfesionalSerializer,
    RegistrarClienteSerializer,
    RegistrarProfesionalSerializer,
)
from apps.cuentas.services import (
    ConsultaPerfilService,
    RegistroClienteService,
    RegistroProfesionalService,
)


class RegistrarClienteView(APIView):

    permission_classes = [AllowAny]
    servicio = RegistroClienteService

    def post(self, request):
        entrada = RegistrarClienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cliente = self.servicio().registrar(entrada.a_comando())
        return Response(ClienteSerializer(cliente).data, status=status.HTTP_201_CREATED)


class RegistrarProfesionalView(APIView):

    permission_classes = [AllowAny]
    servicio = RegistroProfesionalService

    def post(self, request):
        entrada = RegistrarProfesionalSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        profesional = self.servicio().registrar(entrada.a_comando())
        return Response(
            ProfesionalSerializer(profesional).data, status=status.HTTP_201_CREATED
        )


class PerfilView(APIView):

    permission_classes = [IsAuthenticated]
    servicio = ConsultaPerfilService

    def get(self, request):
        perfil = self.servicio.perfil_de(request.user)
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)
