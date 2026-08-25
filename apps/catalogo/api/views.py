from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogo.api.serializers import (
    BusquedaProfesionalesSerializer,
    PublicarServicioSerializer,
    ServicioSerializer,
)
from apps.catalogo.services import CatalogoService, PublicacionServicioService
from apps.comun.api.paginacion import respuesta_paginada
from apps.cuentas.api.serializers import ProfesionalSerializer


class BuscarProfesionalesView(APIView):

    permission_classes = [AllowAny]
    servicio = CatalogoService

    def get(self, request):
        filtros = BusquedaProfesionalesSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        profesionales = self.servicio().buscar_profesionales(
            zona=filtros.validated_data.get("zona", ""),
            texto=filtros.validated_data.get("texto", ""),
            categoria=filtros.validated_data.get("categoria", ""),
        )
        return respuesta_paginada(self, request, profesionales, ProfesionalSerializer)


class ServiciosDelProfesionalView(APIView):

    permission_classes = [AllowAny]
    servicio = CatalogoService

    def get(self, request, profesional_id: int):
        servicios = self.servicio().servicios_de(profesional_id)
        return respuesta_paginada(self, request, servicios, ServicioSerializer)


class MisServiciosView(APIView):
    """Catalogo propio del profesional autenticado.

    GET  -> sus servicios, incluidos los inactivos   200 | 404
    POST -> publica un servicio nuevo                201 | 400 | 404 | 409
    """

    permission_classes = [IsAuthenticated]
    servicio = PublicacionServicioService

    def get(self, request):
        servicios = self.servicio().mis_servicios(request.user.pk)
        return respuesta_paginada(self, request, servicios, ServicioSerializer)

    def post(self, request):
        entrada = PublicarServicioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        creado = self.servicio().publicar(entrada.a_comando(request.user.pk))
        return Response(
            ServicioSerializer(creado).data, status=status.HTTP_201_CREATED
        )
