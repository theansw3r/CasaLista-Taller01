"""
Capa de aplicacion del modulo Cuentas.

Una clase por flujo de negocio (SRP). Cada servicio conoce el ALGORITMO de su
caso de uso y nada mas: no sabe que existe HTTP, no arma respuestas y no
formatea nada.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.cuentas.dominio.excepciones import (
    ClienteNoRegistrado,
    CorreoYaRegistrado,
    ProfesionalNoRegistrado,
)
from apps.cuentas.dto import RegistrarClienteCommand, RegistrarProfesionalCommand
from apps.cuentas.models import Cliente, Profesional

Usuario = get_user_model()


def _exigir_correo_libre(correo: str) -> None:
    """Regla compartida por los dos registros: un correo, una cuenta.

    Es una funcion del modulo y no un metodo, porque no pertenece mas a un
    servicio que al otro. Duplicarla en ambos habria sido peor.
    """
    if Usuario.objects.filter(username=correo).exists():
        raise CorreoYaRegistrado(correo=correo)


class RegistroClienteService:
    """Caso de uso: una persona se registra como cliente."""

    def registrar(self, comando: RegistrarClienteCommand) -> Cliente:
        correo = comando.correo.strip().lower()
        _exigir_correo_libre(correo)

        # La cuenta y el perfil se crean juntos o no se crean: un usuario sin
        # perfil de cliente podria autenticarse y no poder reservar nada.
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                username=correo,
                email=correo,
                password=comando.contrasena,
            )
            return Cliente.objects.create(
                usuario=usuario,
                nombre=comando.nombre.strip(),
                telefono=comando.telefono.strip(),
            )


class RegistroProfesionalService:
    """Caso de uso: una persona se registra como profesional.

    Queda `verificado=False`: segun RN-07 no puede recibir reservas hasta que
    un administrador lo verifique. Esa verificacion es un flujo aparte, no
    parte del registro.
    """

    def registrar(self, comando: RegistrarProfesionalCommand) -> Profesional:
        correo = comando.correo.strip().lower()
        _exigir_correo_libre(correo)

        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                username=correo,
                email=correo,
                password=comando.contrasena,
            )
            return Profesional.objects.create(
                usuario=usuario,
                nombre=comando.nombre.strip(),
                documento=comando.documento.strip(),
                zonas_cobertura=",".join(comando.zonas_cobertura),
                verificado=False,
            )


class ConsultaPerfilService:
    """Caso de uso de lectura: resolver el perfil de la cuenta autenticada.

    Vive en un servicio y no en la vista porque el resto del sistema necesita
    exactamente lo mismo: reservas y pagos tambien tienen que pasar de
    "usuario autenticado" a "cliente del dominio". Si estuviera en la vista,
    esa traduccion estaria copiada en cuatro lugares.
    """

    @staticmethod
    def cliente_de(usuario_id: int) -> Cliente:
        try:
            return Cliente.objects.select_related("usuario").get(usuario_id=usuario_id)
        except Cliente.DoesNotExist:
            raise ClienteNoRegistrado() from None

    @staticmethod
    def profesional_de(usuario_id: int) -> Profesional:
        try:
            return Profesional.objects.select_related("usuario").get(
                usuario_id=usuario_id
            )
        except Profesional.DoesNotExist:
            raise ProfesionalNoRegistrado() from None

    @classmethod
    def perfil_de(cls, usuario) -> dict:
        """Describe la cuenta y los roles que tiene asociados."""
        cliente = Cliente.objects.filter(usuario_id=usuario.pk).first()
        profesional = Profesional.objects.filter(usuario_id=usuario.pk).first()
        return {
            "usuario_id": usuario.pk,
            "correo": usuario.email,
            "cliente": cliente,
            "profesional": profesional,
        }
