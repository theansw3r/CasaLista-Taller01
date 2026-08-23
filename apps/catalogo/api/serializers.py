"""Serializers del modulo Catalogo (todos de salida: el catalogo se lee)."""

from rest_framework import serializers

from apps.catalogo.models import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    """Representacion publica de un item del catalogo."""

    profesional_id = serializers.IntegerField(read_only=True)
    profesional = serializers.CharField(source="profesional.nombre", read_only=True)

    class Meta:
        model = Servicio
        fields = [
            "id",
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
    """Valida los parametros de consulta de la busqueda.

    Se usa un serializer tambien para los `query params` y no se leen a mano
    con `request.query_params.get(...)`: asi el esquema OpenAPI los documenta
    y el API Gateway puede validarlos en el borde, antes de que la peticion
    llegue a la aplicacion.
    """

    zona = serializers.CharField(max_length=80, required=False, allow_blank=True)
    texto = serializers.CharField(max_length=120, required=False, allow_blank=True)
