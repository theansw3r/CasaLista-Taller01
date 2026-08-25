from rest_framework import serializers

from apps.catalogo.dto import PublicarServicioCommand
from apps.catalogo.models import Servicio


class ServicioSerializer(serializers.ModelSerializer):

    profesional_id = serializers.IntegerField(read_only=True)
    profesional = serializers.CharField(source="profesional.nombre", read_only=True)
    categoria_nombre = serializers.CharField(
        source="get_categoria_display", read_only=True
    )

    class Meta:
        model = Servicio
        fields = [
            "id",
            "categoria",
            "categoria_nombre",
            "nombre",
            "descripcion",
            "precio_base",
            "duracion_minutos",
            "requiere_visita_previa",
            "activo",
            "profesional_id",
            "profesional",
        ]
        read_only_fields = fields


class BusquedaProfesionalesSerializer(serializers.Serializer):

    zona = serializers.CharField(max_length=80, required=False, allow_blank=True)
    texto = serializers.CharField(max_length=120, required=False, allow_blank=True)
    categoria = serializers.ChoiceField(
        choices=Servicio.Oficio.choices, required=False, allow_blank=True
    )


class PublicarServicioSerializer(serializers.Serializer):
    """Cuerpo de POST /api/v1/catalogo/mis-servicios/."""

    categoria = serializers.ChoiceField(choices=Servicio.Oficio.choices)
    nombre = serializers.CharField(max_length=120)
    descripcion = serializers.CharField(max_length=500)
    precio_base = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    duracion_minutos = serializers.IntegerField()
    requiere_visita_previa = serializers.BooleanField(required=False, default=False)

    def a_comando(self, usuario_id: int) -> PublicarServicioCommand:
        datos = self.validated_data
        return PublicarServicioCommand(
            usuario_id=usuario_id,
            categoria=datos["categoria"],
            nombre=datos["nombre"],
            descripcion=datos.get("descripcion", ""),
            precio_base=datos["precio_base"],
            duracion_minutos=datos["duracion_minutos"],
            requiere_visita_previa=datos.get("requiere_visita_previa", False),
        )
