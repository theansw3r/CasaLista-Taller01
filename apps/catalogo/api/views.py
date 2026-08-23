"""
Capa de presentacion del modulo Catalogo.

El catalogo es publico: sin token no se puede reservar, pero si mirar. Es la
unica parte de la API con `AllowAny`, y es tambien la que mas trafico recibe,
por eso es la primera candidata a cachearse en el API Gateway.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.catalogo.api.serializers import (
    BusquedaProfesionalesSerializer,
    ServicioSerializer,
)
from apps.catalogo.services import CatalogoService
from apps.comun.api.paginacion import respuesta_paginada
from apps.cuentas.api.serializers import ProfesionalSerializer


class BuscarProfesionalesView(APIView):
    """GET /api/v1/catalogo/profesionales/?zona=&texto= -> 200 | 400."""

    permission_classes = [AllowAny]
    servicio = CatalogoService

    @extend_schema(
        summary="Buscar profesionales verificados que cubran una zona (RN-07)",
        parameters=[
            OpenApiParameter("zona", str, description="Ej: Laureles"),
            OpenApiParameter("texto", str, description="Busca en el nombre"),
        ],
        responses={200: ProfesionalSerializer(many=True)},
        tags=["catalogo"],
    )
    def get(self, request):
        filtros = BusquedaProfesionalesSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        profesionales = self.servicio().buscar_profesionales(
            zona=filtros.validated_data.get("zona", ""),
            texto=filtros.validated_data.get("texto", ""),
        )
        return respuesta_paginada(self, request, profesionales, ProfesionalSerializer)


class ServiciosDelProfesionalView(APIView):
    """GET /api/v1/catalogo/profesionales/<id>/servicios/ -> 200 | 404."""

    permission_classes = [AllowAny]
    servicio = CatalogoService

    @extend_schema(
        summary="Catalogo publicado por un profesional",
        responses={200: ServicioSerializer(many=True)},
        tags=["catalogo"],
    )
    def get(self, request, profesional_id: int):
        servicios = self.servicio().servicios_de(profesional_id)
        return respuesta_paginada(self, request, servicios, ServicioSerializer)
