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
    if Usuario.objects.filter(username=correo).exists():
        raise CorreoYaRegistrado(correo=correo)


class RegistroClienteService:

    def registrar(self, comando: RegistrarClienteCommand) -> Cliente:
        correo = comando.correo.strip().lower()
        _exigir_correo_libre(correo)

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
                descripcion=comando.descripcion.strip(),
                zonas_cobertura=",".join(comando.zonas_cobertura),
                verificado=False,
            )


class ConsultaPerfilService:

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
        cliente = Cliente.objects.filter(usuario_id=usuario.pk).first()
        profesional = Profesional.objects.filter(usuario_id=usuario.pk).first()
        return {
            "usuario_id": usuario.pk,
            "correo": usuario.email,
            "cliente": cliente,
            "profesional": profesional,
        }


class VerificacionProfesionalService:
    """Caso de uso: el administrador habilita a un profesional (RN-07).

    Es la puerta que decide quien puede recibir reservas, asi que es logica de
    negocio y vive aqui, no en `admin.py`. El panel de administracion es solo
    una interfaz mas que llama a este servicio, igual que lo haria una vista.
    """

    def verificar(self, profesionales) -> int:
        """Habilita a los profesionales indicados. Devuelve cuantos cambiaron."""
        return profesionales.update(verificado=True)

    def revocar(self, profesionales) -> int:
        """Quita la verificacion: dejan de aparecer en las busquedas."""
        return profesionales.update(verificado=False)
