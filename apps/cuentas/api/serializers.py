from rest_framework import serializers

from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.dto import RegistrarClienteCommand, RegistrarProfesionalCommand
from apps.cuentas.models import Cliente, Profesional

LARGO_MINIMO_CONTRASENA = 8


class RegistrarClienteSerializer(serializers.Serializer):

    correo = serializers.EmailField()
    contrasena = serializers.CharField(
        write_only=True, min_length=LARGO_MINIMO_CONTRASENA
    )
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def a_comando(self) -> RegistrarClienteCommand:
        datos = self.validated_data
        return RegistrarClienteCommand(
            correo=datos["correo"],
            contrasena=datos["contrasena"],
            nombre=datos["nombre"],
            telefono=datos.get("telefono", ""),
        )


class RegistrarProfesionalSerializer(serializers.Serializer):

    correo = serializers.EmailField()
    contrasena = serializers.CharField(
        write_only=True, min_length=LARGO_MINIMO_CONTRASENA
    )
    nombre = serializers.CharField(max_length=120)
    documento = serializers.CharField(max_length=30)
    descripcion = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    zonas_cobertura = serializers.ListField(
        child=serializers.CharField(max_length=80),
        allow_empty=True,
        required=False,
        default=list,
        help_text='Ej: ["Laureles", "Belen"]',
    )

    def a_comando(self) -> RegistrarProfesionalCommand:
        datos = self.validated_data
        return RegistrarProfesionalCommand(
            correo=datos["correo"],
            contrasena=datos["contrasena"],
            nombre=datos["nombre"],
            documento=datos["documento"],
            descripcion=datos.get("descripcion", ""),
            zonas_cobertura=tuple(datos.get("zonas_cobertura", [])),
        )


class ClienteSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "correo", "telefono", "creado_en"]
        read_only_fields = fields


class ProfesionalSerializer(serializers.ModelSerializer):
    zonas = serializers.SerializerMethodField()

    class Meta:
        model = Profesional
        fields = [
            "id",
            "nombre",
            "descripcion",
            "verificado",
            "zonas",
            "calificacion_promedio",
        ]
        read_only_fields = fields

    def get_zonas(self, profesional: Profesional) -> list[str]:
        return PoliticaDeCobertura.zonas_de(profesional)


class PerfilSerializer(serializers.Serializer):

    usuario_id = serializers.IntegerField(read_only=True)
    correo = serializers.EmailField(read_only=True)
    cliente = ClienteSerializer(read_only=True, allow_null=True)
    profesional = ProfesionalSerializer(read_only=True, allow_null=True)
