"""Helpers para armar escenarios de prueba sin repetir 20 lineas en cada test."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from ..models import BloqueDisponibilidad, Cliente, Profesional, Servicio


def crear_cliente(nombre="Ana Cliente", email="ana@casalista.co") -> Cliente:
    usuario = User.objects.create_user(
        username=email, email=email, password="clave-de-prueba"
    )
    return Cliente.objects.create(usuario=usuario, nombre=nombre, telefono="3000000000")


def crear_profesional(
    nombre="Pedro Plomero",
    verificado=True,
    zonas="Laureles,Belen",
    email="pedro@casalista.co",
) -> Profesional:
    usuario = User.objects.create_user(
        username=email, email=email, password="clave-de-prueba"
    )
    return Profesional.objects.create(
        usuario=usuario,
        nombre=nombre,
        verificado=verificado,
        zonas_cobertura=zonas,
    )


def crear_servicio(
    profesional, nombre="Reparacion de fuga", precio="80000", duracion=60, activo=True
) -> Servicio:
    return Servicio.objects.create(
        profesional=profesional,
        nombre=nombre,
        precio_base=Decimal(precio),
        duracion_minutos=duracion,
        activo=activo,
    )


def crear_bloque(profesional, inicio=None, horas=2) -> BloqueDisponibilidad:
    """Por defecto, un martes a las 10:00 (dia habil y horario diurno)."""
    if inicio is None:
        inicio = timezone.localtime(timezone.now()).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        while inicio.weekday() != 1:  # martes
            inicio += timedelta(days=1)
    return BloqueDisponibilidad.objects.create(
        profesional=profesional, inicio=inicio, fin=inicio + timedelta(hours=horas)
    )


class NotificadorEspia:
    """Doble de prueba: registra a quien se le notifico, sin enviar nada."""

    nombre = "ESPIA"

    def __init__(self):
        self.enviados = []

    def enviar_confirmacion_reserva(self, reserva) -> None:
        self.enviados.append(reserva)
