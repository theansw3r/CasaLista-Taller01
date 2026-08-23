"""
Capa de presentacion del modulo Agenda y Reservas.

Todas son `APIView`. Ninguna tiene reglas de negocio, consultas al ORM ni
try/except: si algo falla, el dominio lanza su excepcion y el manejador
central (`apps.comun.api.manejador_errores`) decide el codigo de estado.

Mapa de codigos que puede devolver este modulo:

    201  la reserva o la franja se creo
    200  consulta o cancelacion procesada
    400  el cuerpo no tiene la forma esperada (lo rechaza el serializer)
    403  la reserva existe pero es de otro cliente
    404  el bloque, el servicio o la reserva no existen
    409  la peticion choca con el estado del sistema (RN-01, RN-02, RN-07...)
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reservas.api.serializers import (
    AbrirDisponibilidadSerializer,
    BloqueSerializer,
    CancelarReservaSerializer,
    ConsultarDisponibilidadSerializer,
    CrearReservaSerializer,
    ReservaSerializer,
)
from apps.reservas.services import (
    AgendaService,
    CancelacionReservaService,
    ConsultaReservasService,
    ReservaService,
)


class DisponibilidadView(APIView):
    """Franjas de agenda.

    GET  -> consulta publica de franjas libres        200 | 400
    POST -> el profesional publica una franja nueva   201 | 400 | 404 | 409
    """

    servicio = AgendaService

    def get_permissions(self):
        # Consultar la agenda es publico (es parte de la vitrina); publicar
        # requiere ser el profesional dueno de esa agenda.
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Consultar franjas libres de un profesional",
        parameters=[
            OpenApiParameter("profesional_id", int, required=True),
            OpenApiParameter("desde", str, description="ISO-8601"),
        ],
        responses={200: BloqueSerializer(many=True)},
        tags=["agenda"],
    )
    def get(self, request):
        filtros = ConsultarDisponibilidadSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        bloques = self.servicio().bloques_libres(
            profesional_id=filtros.validated_data["profesional_id"],
            desde=filtros.validated_data.get("desde"),
        )
        return Response(
            BloqueSerializer(bloques, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Publicar una franja de disponibilidad",
        request=AbrirDisponibilidadSerializer,
        responses={201: BloqueSerializer},
        tags=["agenda"],
    )
    def post(self, request):
        entrada = AbrirDisponibilidadSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        bloque = self.servicio().abrir_disponibilidad(
            entrada.a_comando(request.user.pk)
        )
        return Response(BloqueSerializer(bloque).data, status=status.HTTP_201_CREATED)


class ReservasView(APIView):
    """Coleccion de reservas del cliente autenticado.

    GET  -> sus reservas                 200
    POST -> crea una reserva nueva       201 | 400 | 404 | 409

    El POST es el flujo mas complejo del sistema: dispara el Builder, las dos
    Factories y una transaccion con bloqueo. Aun asi la vista tiene cuatro
    lineas, porque no participa en nada de eso.
    """

    permission_classes = [IsAuthenticated]
    servicio_consulta = ConsultaReservasService
    servicio_creacion = ReservaService

    @extend_schema(
        summary="Listar las reservas del cliente autenticado",
        responses={200: ReservaSerializer(many=True)},
        tags=["reservas"],
    )
    def get(self, request):
        reservas = self.servicio_consulta().reservas_de(request.user.pk)
        return Response(
            ReservaSerializer(reservas, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Crear una reserva (Builder + Factory)",
        request=CrearReservaSerializer,
        responses={201: ReservaSerializer},
        tags=["reservas"],
    )
    def post(self, request):
        entrada = CrearReservaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = self.servicio_creacion().crear_reserva(
            entrada.a_comando(request.user.pk)
        )
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)


class ReservaDetalleView(APIView):
    """GET /api/v1/reservas/<id>/ -> 200 | 403 | 404."""

    permission_classes = [IsAuthenticated]
    servicio = ConsultaReservasService

    @extend_schema(
        summary="Detalle de una reserva propia",
        responses={200: ReservaSerializer},
        tags=["reservas"],
    )
    def get(self, request, reserva_id: int):
        reserva = self.servicio().detalle_de(request.user.pk, reserva_id)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)


class CancelarReservaView(APIView):
    """POST /api/v1/reservas/<id>/cancelacion/ -> 200 | 403 | 404 | 409.

    Se modela como un recurso hijo (`/cancelacion/`) y no como un DELETE
    porque cancelar no borra: cambia el estado, calcula una penalizacion y
    libera la franja. Un DELETE sugeriria que la reserva desaparece, y el
    negocio necesita conservarla para la liquidacion.
    """

    permission_classes = [IsAuthenticated]
    servicio = CancelacionReservaService

    @extend_schema(
        summary="Cancelar una reserva (RN-04: calcula la penalizacion)",
        request=CancelarReservaSerializer,
        responses={200: ReservaSerializer},
        tags=["reservas"],
    )
    def post(self, request, reserva_id: int):
        entrada = CancelarReservaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = self.servicio().cancelar(
            entrada.a_comando(request.user.pk, reserva_id)
        )
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)
