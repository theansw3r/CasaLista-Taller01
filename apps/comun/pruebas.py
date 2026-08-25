from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalogo.models import Servicio
from apps.cuentas.models import Cliente, Profesional
from apps.pagos.dominio.puertos import PasarelaDePago, ResultadoPago
from apps.reservas.dominio.puertos import Notificador
from apps.reservas.models import BloqueDisponibilidad

Usuario = get_user_model()

CONTRASENA = "prueba-segura-123"

_contador = {"n": 0}


def _siguiente() -> int:
    _contador["n"] += 1
    return _contador["n"]


def crear_cliente(nombre: str = "Cliente de prueba") -> Cliente:
    numero = _siguiente()
    usuario = Usuario.objects.create_user(
        username=f"cliente{numero}@prueba.co",
        email=f"cliente{numero}@prueba.co",
        password=CONTRASENA,
    )
    return Cliente.objects.create(usuario=usuario, nombre=nombre, telefono="3000000000")


def crear_profesional(
    nombre: str = "Profesional de prueba",
    verificado: bool = True,
    zonas: str = "Laureles,Belen",
) -> Profesional:
    numero = _siguiente()
    usuario = Usuario.objects.create_user(
        username=f"pro{numero}@prueba.co",
        email=f"pro{numero}@prueba.co",
        password=CONTRASENA,
    )
    return Profesional.objects.create(
        usuario=usuario,
        nombre=nombre,
        documento=f"DOC-{numero}",
        verificado=verificado,
        zonas_cobertura=zonas,
    )


def crear_servicio(
    profesional: Profesional,
    nombre: str = "Servicio de prueba",
    precio: str = "50000",
    minutos: int = 60,
    activo: bool = True,
    categoria: str = Servicio.Oficio.PLOMERIA,
) -> Servicio:
    return Servicio.objects.create(
        profesional=profesional,
        categoria=categoria,
        nombre=f"{nombre} {_siguiente()}",
        descripcion="Servicio creado para las pruebas automaticas.",
        precio_base=Decimal(precio),
        duracion_minutos=minutos,
        activo=activo,
    )


def crear_bloque(
    profesional: Profesional,
    dentro_de_horas: int = 48,
    duracion_horas: int = 2,
) -> BloqueDisponibilidad:
    inicio = timezone.now() + timedelta(hours=dentro_de_horas)
    return BloqueDisponibilidad.objects.create(
        profesional=profesional,
        inicio=inicio,
        fin=inicio + timedelta(hours=duracion_horas),
    )


def escenario_basico() -> dict:
    profesional = crear_profesional()
    return {
        "cliente": crear_cliente(),
        "profesional": profesional,
        "servicio": crear_servicio(profesional),
        "bloque": crear_bloque(profesional),
    }


class NotificadorEspia(Notificador):

    nombre = "ESPIA"

    def __init__(self) -> None:
        self.avisos = []

    def enviar_confirmacion_reserva(self, reserva) -> None:
        self.avisos.append(reserva.pk)


class PasarelaQueRechaza(PasarelaDePago):

    nombre = "RECHAZA"

    def cobrar(self, monto, referencia_interna) -> ResultadoPago:
        return ResultadoPago(aprobado=False, motivo="Fondos insuficientes.")


class PasarelaQueAprueba(PasarelaDePago):

    nombre = "APRUEBA"

    def cobrar(self, monto, referencia_interna) -> ResultadoPago:
        return ResultadoPago(aprobado=True, referencia="REF-PRUEBA-001")
