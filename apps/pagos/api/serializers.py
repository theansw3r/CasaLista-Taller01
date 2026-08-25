from rest_framework import serializers

from apps.pagos.dto import ProcesarPagoCommand
from apps.pagos.models import Pago


class ProcesarPagoSerializer(serializers.Serializer):

    reserva_id = serializers.IntegerField(min_value=1)
    medio = serializers.ChoiceField(choices=Pago.Medio.choices)

    def a_comando(self, usuario_id: int) -> ProcesarPagoCommand:
        datos = self.validated_data
        return ProcesarPagoCommand(
            usuario_id=usuario_id,
            reserva_id=datos["reserva_id"],
            medio=datos["medio"],
        )


class PagoSerializer(serializers.ModelSerializer):

    reserva_id = serializers.IntegerField(read_only=True)
    estado_reserva = serializers.CharField(source="reserva.estado", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "reserva_id",
            "estado_reserva",
            "monto",
            "medio",
            "estado",
            "pasarela",
            "referencia_externa",
            "creado_en",
        ]
        read_only_fields = fields
