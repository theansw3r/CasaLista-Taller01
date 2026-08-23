"""
Capa de presentacion del modulo Cuentas.

Todas las vistas son `APIView`, no ViewSets. Se eligio APIView porque el
enunciado pide control total de la peticion: aqui se ve explicitamente que
metodo HTTP se atiende, que serializer valida y que codigo de estado sale.

El contrato que cumple cada vista es siempre el mismo, en cuatro pasos:

    1. validar la FORMA con un serializer de entrada  -> 400 si falla
    2. traducir a un comando (dataclass)
    3. delegar en el servicio                          -> 404 / 409 si falla
    4. serializar el resultado y elegir el codigo      -> 201 / 200

No hay try/except: las excepciones de dominio las traduce
`apps.comun.api.manejador_errores`. No hay consultas al ORM. No hay una sola
regla de negocio.
"""

from drf_spectacular.utils import extend_schema
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
    """POST /api/v1/cuentas/registro/cliente/ -> 201 | 400."""

    permission_classes = [AllowAny]
    # El servicio es un atributo de clase para poder sustituirlo en las
    # pruebas: `RegistrarClienteView.as_view(servicio=ServicioEspia)`.
    servicio = RegistroClienteService

    @extend_schema(
        summary="Registrar un cliente",
        request=RegistrarClienteSerializer,
        responses={201: ClienteSerializer},
        tags=["cuentas"],
    )
    def post(self, request):
        entrada = RegistrarClienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cliente = self.servicio().registrar(entrada.a_comando())
        return Response(ClienteSerializer(cliente).data, status=status.HTTP_201_CREATED)


class RegistrarProfesionalView(APIView):
    """POST /api/v1/cuentas/registro/profesional/ -> 201 | 400."""

    permission_classes = [AllowAny]
    servicio = RegistroProfesionalService

    @extend_schema(
        summary="Registrar un profesional (queda pendiente de verificacion)",
        request=RegistrarProfesionalSerializer,
        responses={201: ProfesionalSerializer},
        tags=["cuentas"],
    )
    def post(self, request):
        entrada = RegistrarProfesionalSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        profesional = self.servicio().registrar(entrada.a_comando())
        return Response(
            ProfesionalSerializer(profesional).data, status=status.HTTP_201_CREATED
        )


class PerfilView(APIView):
    """GET /api/v1/cuentas/perfil/ -> 200 con los roles de la cuenta."""

    permission_classes = [IsAuthenticated]
    servicio = ConsultaPerfilService

    @extend_schema(
        summary="Perfil de la cuenta autenticada",
        responses={200: PerfilSerializer},
        tags=["cuentas"],
    )
    def get(self, request):
        perfil = self.servicio.perfil_de(request.user)
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)
