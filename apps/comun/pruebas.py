"""
Ayudas para las pruebas: fabrica de datos y dobles de prueba.

Vive en `comun` porque las usan las cuatro apps. Sin esto, cada archivo de
prueba repetiria treinta lineas de preparacion y una prueba fallaria por
razones que no tienen que ver con lo que quiere comprobar.
"""

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
    """Contador para que los correos y documentos no se repitan."""
    _contador["n"] += 1
    return _contador["n"]


# ---------------------------------------------------------------------------
# Fabrica de datos
# ---------------------------------------------------------------------------
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
) -> Servicio:
    return Servicio.objects.create(
        profesional=profesional,
        nombre=f"{nombre} {_siguiente()}",
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
    """Un cliente, un profesional verificado, un servicio y una franja libre.

    Es el punto de partida de casi toda prueba de reservas.
    """
    profesional = crear_profesional()
    return {
        "cliente": crear_cliente(),
        "profesional": profesional,
        "servicio": crear_servicio(profesional),
        "bloque": crear_bloque(profesional),
    }


# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------
class NotificadorEspia(Notificador):
    """Notificador que solo registra a quien se le aviso.

    Sirve para comprobar que el servicio notifica, sin mandar un correo y sin
    depender de una variable de entorno.
    """

    nombre = "ESPIA"

    def __init__(self) -> None:
        self.avisos = []

    def enviar_confirmacion_reserva(self, reserva) -> None:
        self.avisos.append(reserva.pk)


class PasarelaQueRechaza(PasarelaDePago):
    """Pasarela que siempre dice que no. Para probar el camino de rechazo."""

    nombre = "RECHAZA"

    def cobrar(self, monto, referencia_interna) -> ResultadoPago:
        return ResultadoPago(aprobado=False, motivo="Fondos insuficientes.")


class PasarelaQueAprueba(PasarelaDePago):
    """Pasarela que siempre aprueba, con una referencia predecible."""

    nombre = "APRUEBA"

    def cobrar(self, monto, referencia_interna) -> ResultadoPago:
        return ResultadoPago(aprobado=True, referencia="REF-PRUEBA-001")
