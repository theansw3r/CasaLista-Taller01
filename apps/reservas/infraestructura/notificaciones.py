import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.reservas.dominio.puertos import Notificador

logger = logging.getLogger(__name__)


def _asunto(reserva) -> str:
    return f"CasaLista - Reserva #{reserva.pk} creada"


def _cuerpo(reserva) -> str:
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

    nombre = "MOCK"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        logger.info("[MOCK] %s | %s", _asunto(reserva), reserva.cliente.nombre)


class NotificadorEmail(Notificador):

    nombre = "REAL"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        destinatario = getattr(reserva.cliente.usuario, "email", "")
        if not destinatario:
            logger.warning("Reserva %s: el cliente no tiene correo.", reserva.pk)
            return
        send_mail(
            subject=_asunto(reserva),
            message=_cuerpo(reserva),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=True,
        )
