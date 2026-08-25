from rest_framework import serializers

from apps.reservas.dominio.agenda import ReglasAgenda
from apps.reservas.dominio.precios import CalculadoraDeReserva
from apps.reservas.dto import (
    AbrirDisponibilidadCommand,
    CancelarReservaCommand,
    CrearReservaCommand,
    LineaSolicitada,
)
from apps.reservas.models import BloqueDisponibilidad, DetalleReserva, Reserva


class LineaSolicitadaSerializer(serializers.Serializer):

    servicio_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CrearReservaSerializer(serializers.Serializer):

    bloque_id = serializers.IntegerField(min_value=1)
    direccion = serializers.CharField(max_length=180)
    zona = serializers.CharField(max_length=80)
    servicios = LineaSolicitadaSerializer(many=True, allow_empty=False)

    def a_comando(self, usuario_id: int) -> CrearReservaCommand:
        datos = self.validated_data
        return CrearReservaCommand(
            usuario_id=usuario_id,
            bloque_id=datos["bloque_id"],
            direccion=datos["direccion"],
            zona=datos["zona"],
            lineas=tuple(
                LineaSolicitada(
                    servicio_id=linea["servicio_id"], cantidad=linea["cantidad"]
                )
                for linea in datos["servicios"]
            ),
        )


class AbrirDisponibilidadSerializer(serializers.Serializer):

    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()

    def a_comando(self, usuario_id: int) -> AbrirDisponibilidadCommand:
        datos = self.validated_data
        return AbrirDisponibilidadCommand(
            usuario_id=usuario_id, inicio=datos["inicio"], fin=datos["fin"]
        )


class ConsultarDisponibilidadSerializer(serializers.Serializer):

    profesional_id = serializers.IntegerField(min_value=1)
    desde = serializers.DateTimeField(required=False)


class CancelarReservaSerializer(serializers.Serializer):

    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def a_comando(self, usuario_id: int, reserva_id: int) -> CancelarReservaCommand:
        return CancelarReservaCommand(
            usuario_id=usuario_id,
            reserva_id=reserva_id,
            motivo=self.validated_data.get("motivo", ""),
        )


class BloqueSerializer(serializers.ModelSerializer):
    duracion_minutos = serializers.SerializerMethodField()
    profesional = serializers.CharField(source="profesional.nombre", read_only=True)

    class Meta:
        model = BloqueDisponibilidad
        fields = ["id", "profesional", "inicio", "fin", "duracion_minutos", "estado"]
        read_only_fields = fields

    def get_duracion_minutos(self, bloque) -> int:
        return ReglasAgenda.duracion_minutos(bloque)


class DetalleReservaSerializer(serializers.ModelSerializer):
    servicio = serializers.CharField(source="servicio.nombre", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = DetalleReserva
        fields = [
            "servicio",
            "cantidad",
            "precio_unitario",
            "duracion_unitaria_minutos",
            "subtotal",
        ]
        read_only_fields = fields

    def get_subtotal(self, detalle) -> str:
        return str(CalculadoraDeReserva.subtotal(detalle))


class ReservaSerializer(serializers.ModelSerializer):

    cliente = serializers.CharField(source="cliente.nombre", read_only=True)
    profesional = serializers.CharField(source="profesional.nombre", read_only=True)
    inicio = serializers.DateTimeField(source="bloque.inicio", read_only=True)
    fin = serializers.DateTimeField(source="bloque.fin", read_only=True)
    detalles = DetalleReservaSerializer(many=True, read_only=True)

    class Meta:
        model = Reserva
        fields = [
            "id",
            "estado",
            "cliente",
            "profesional",
            "direccion",
            "zona",
            "inicio",
            "fin",
            "total",
            "tarifa_aplicada",
            "penalizacion",
            "detalles",
            "creada_en",
        ]
        read_only_fields = fields
