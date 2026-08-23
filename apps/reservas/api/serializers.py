"""
Serializers del modulo Agenda y Reservas.

Los de entrada validan FORMA, nunca negocio. La frontera es facil de trazar
con una pregunta: "para responder esto, ¿hay que consultar la base de datos o
conocer una regla?". Si la respuesta es si, no va aqui.

    validar que `cantidad` sea un entero >= 1   -> forma   (aqui)
    validar que la franja siga libre            -> negocio (Builder)
    validar que el bloque exista                -> negocio (Service)
    validar que el total incluya recargo        -> negocio (estrategia)
"""

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


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
class LineaSolicitadaSerializer(serializers.Serializer):
    """Una linea del cuerpo de la reserva."""

    servicio_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CrearReservaSerializer(serializers.Serializer):
    """Cuerpo de POST /api/v1/reservas/."""

    bloque_id = serializers.IntegerField(min_value=1)
    direccion = serializers.CharField(max_length=180)
    zona = serializers.CharField(max_length=80)
    servicios = LineaSolicitadaSerializer(many=True, allow_empty=False)

    def a_comando(self, usuario_id: int) -> CrearReservaCommand:
        """Traduce el cuerpo validado al comando del servicio.

        Es mapeo de estructuras, no logica: aqui no se decide nada, solo se
        cambia de formato. La reserva la decide el Builder.
        """
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
    """Cuerpo de POST /api/v1/reservas/disponibilidad/."""

    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()

    def a_comando(self, usuario_id: int) -> AbrirDisponibilidadCommand:
        datos = self.validated_data
        return AbrirDisponibilidadCommand(
            usuario_id=usuario_id, inicio=datos["inicio"], fin=datos["fin"]
        )


class ConsultarDisponibilidadSerializer(serializers.Serializer):
    """Parametros de GET /api/v1/reservas/disponibilidad/."""

    profesional_id = serializers.IntegerField(min_value=1)
    desde = serializers.DateTimeField(required=False)


class CancelarReservaSerializer(serializers.Serializer):
    """Cuerpo de POST /api/v1/reservas/<id>/cancelacion/."""

    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def a_comando(self, usuario_id: int, reserva_id: int) -> CancelarReservaCommand:
        return CancelarReservaCommand(
            usuario_id=usuario_id,
            reserva_id=reserva_id,
            motivo=self.validated_data.get("motivo", ""),
        )


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------
class BloqueSerializer(serializers.ModelSerializer):
    duracion_minutos = serializers.SerializerMethodField()
    profesional = serializers.CharField(source="profesional.nombre", read_only=True)

    class Meta:
        model = BloqueDisponibilidad
        fields = ["id", "profesional", "inicio", "fin", "duracion_minutos", "estado"]
        read_only_fields = fields

    def get_duracion_minutos(self, bloque) -> int:
        # El calculo lo hace el dominio; el serializer solo lo publica.
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
    """Representacion completa de una reserva."""

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
