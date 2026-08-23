"""
Serializers del modulo Cuentas.

Se separan en dos familias y esa separacion es intencional:

* Los de ENTRADA validan FORMA: que el correo parezca un correo, que la
  contrasena tenga largo minimo, que el campo no venga vacio. Nunca preguntan
  a la base de datos ni deciden nada del negocio.
* Los de SALIDA arman la representacion publica de una entidad.

Un serializer nunca guarda: no hay `create()` ni `update()` en este archivo.
Guardar es responsabilidad del servicio.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.dto import RegistrarClienteCommand, RegistrarProfesionalCommand
from apps.cuentas.models import Cliente, Profesional

LARGO_MINIMO_CONTRASENA = 8


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
class RegistrarClienteSerializer(serializers.Serializer):
    """Cuerpo de POST /api/v1/cuentas/registro/cliente/."""

    correo = serializers.EmailField()
    contrasena = serializers.CharField(
        write_only=True, min_length=LARGO_MINIMO_CONTRASENA
    )
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def a_comando(self) -> RegistrarClienteCommand:
        """Traduce el cuerpo validado al comando que espera el servicio.

        Esto es mapeo, no logica: no hay ninguna decision de negocio aqui.
        """
        datos = self.validated_data
        return RegistrarClienteCommand(
            correo=datos["correo"],
            contrasena=datos["contrasena"],
            nombre=datos["nombre"],
            telefono=datos.get("telefono", ""),
        )


class RegistrarProfesionalSerializer(serializers.Serializer):
    """Cuerpo de POST /api/v1/cuentas/registro/profesional/."""

    correo = serializers.EmailField()
    contrasena = serializers.CharField(
        write_only=True, min_length=LARGO_MINIMO_CONTRASENA
    )
    nombre = serializers.CharField(max_length=120)
    documento = serializers.CharField(max_length=30)
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
            zonas_cobertura=tuple(datos.get("zonas_cobertura", [])),
        )


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------
class ClienteSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "correo", "telefono", "creado_en"]
        read_only_fields = fields


class ProfesionalSerializer(serializers.ModelSerializer):
    # El campo `zonas_cobertura` se guarda como texto separado por comas. Aqui
    # se publica como lista, pero quien sabe partir ese texto es la politica de
    # dominio, no el serializer: el serializer solo pregunta y presenta.
    zonas = serializers.SerializerMethodField()

    class Meta:
        model = Profesional
        fields = [
            "id",
            "nombre",
            "verificado",
            "zonas",
            "calificacion_promedio",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_zonas(self, profesional: Profesional) -> list[str]:
        return PoliticaDeCobertura.zonas_de(profesional)


class PerfilSerializer(serializers.Serializer):
    """Respuesta de GET /api/v1/cuentas/perfil/."""

    usuario_id = serializers.IntegerField(read_only=True)
    correo = serializers.EmailField(read_only=True)
    cliente = ClienteSerializer(read_only=True, allow_null=True)
    profesional = ProfesionalSerializer(read_only=True, allow_null=True)
