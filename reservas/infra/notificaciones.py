"""
Adaptadores del puerto `Notificador`.

Ambos cumplen el mismo contrato, asi que el Service puede recibir cualquiera
sin enterarse (Principio de Sustitucion de Liskov).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from ..domain.puertos import Notificador

logger = logging.getLogger(__name__)


def _asunto(reserva) -> str:
    return f"CasaLista - Reserva #{reserva.pk} creada"


def _cuerpo(reserva) -> str:
    # El cliente lee la hora de su cita en su propia zona horaria, no en UTC.
    inicio = timezone.localtime(reserva.bloque.inicio)
    return (
        f"Hola {reserva.cliente.nombre},\n\n"
        f"Tu reserva con {reserva.profesional.nombre} quedo registrada.\n"
        f"Fecha: {inicio:%d/%m/%Y %H:%M}\n"
        f"Direccion: {reserva.direccion} ({reserva.zona})\n"
        f"Total: $ {reserva.total}\n"
        f"Estado: {reserva.get_estado_display()}\n\n"
        f"Te avisaremos cuando confirmemos el pago."
    )


class NotificadorConsola(Notificador):
    """Implementacion MOCK: deja rastro en el log y no sale de la maquina."""

    nombre = "MOCK"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        logger.info("[MOCK] %s\n%s", _asunto(reserva), _cuerpo(reserva))
        print(f"[NotificadorConsola] {_asunto(reserva)}")


class NotificadorEmail(Notificador):
    """Implementacion REAL: envia el correo con el backend de Django."""

    nombre = "REAL"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        destinatario = getattr(reserva.cliente.usuario, "email", "")
        if not destinatario:
            logger.warning("Reserva %s: el cliente no tiene correo.", reserva.pk)
            return
        # Una notificacion fallida no puede tumbar una reserva ya guardada.
        send_mail(
            subject=_asunto(reserva),
            message=_cuerpo(reserva),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=True,
        )
