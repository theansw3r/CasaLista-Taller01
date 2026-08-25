from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.api.paginacion import respuesta_paginada
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

    servicio = AgendaService

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        filtros = ConsultarDisponibilidadSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        bloques = self.servicio().bloques_libres(
            profesional_id=filtros.validated_data["profesional_id"],
            desde=filtros.validated_data.get("desde"),
        )
        return respuesta_paginada(self, request, bloques, BloqueSerializer)

    def post(self, request):
        entrada = AbrirDisponibilidadSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        bloque = self.servicio().abrir_disponibilidad(
            entrada.a_comando(request.user.pk)
        )
        return Response(BloqueSerializer(bloque).data, status=status.HTTP_201_CREATED)


class ReservasView(APIView):

    permission_classes = [IsAuthenticated]
    servicio_consulta = ConsultaReservasService
    servicio_creacion = ReservaService

    def get(self, request):
        reservas = self.servicio_consulta().reservas_de(request.user.pk)
        return respuesta_paginada(self, request, reservas, ReservaSerializer)

    def post(self, request):
        entrada = CrearReservaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = self.servicio_creacion().crear_reserva(
            entrada.a_comando(request.user.pk)
        )
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)


class ReservaDetalleView(APIView):

    permission_classes = [IsAuthenticated]
    servicio = ConsultaReservasService

    def get(self, request, reserva_id: int):
        reserva = self.servicio().detalle_de(request.user.pk, reserva_id)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)


class CancelarReservaView(APIView):

    permission_classes = [IsAuthenticated]
    servicio = CancelacionReservaService

    def post(self, request, reserva_id: int):
        entrada = CancelarReservaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = self.servicio().cancelar(
            entrada.a_comando(request.user.pk, reserva_id)
        )
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)


class MiAgendaView(APIView):
    """GET /api/v1/reservas/mi-agenda/ -> franjas del profesional autenticado."""

    permission_classes = [IsAuthenticated]
    servicio = AgendaService

    def get(self, request):
        bloques = self.servicio().mi_agenda(request.user.pk)
        return respuesta_paginada(self, request, bloques, BloqueSerializer)


class ReservasRecibidasView(APIView):
    """GET /api/v1/reservas/recibidas/ -> reservas que le hicieron al profesional."""

    permission_classes = [IsAuthenticated]
    servicio = AgendaService

    def get(self, request):
        reservas = self.servicio().reservas_recibidas(request.user.pk)
        return respuesta_paginada(self, request, reservas, ReservaSerializer)
