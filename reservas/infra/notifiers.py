import logging
from typing import Protocol

from django.conf import settings
from django.core.mail import send_mail

from reservas.models import Reserva

logger = logging.getLogger(__name__)


class NotificadorReserva(Protocol):
    def enviar_reserva_creada(self, reserva: Reserva) -> None:
        ...


class ConsolaNotificador:
    def enviar_reserva_creada(self, reserva: Reserva) -> None:
        logger.info(
            "Reserva creada: id=%s cliente=%s total=%s",
            reserva.pk,
            reserva.cliente_id,
            reserva.total,
        )


class EmailNotificador:
    def enviar_reserva_creada(self, reserva: Reserva) -> None:
        destinatario = getattr(reserva.cliente, "email", "")
        if not destinatario:
            logger.warning(
                "No se envió correo para la reserva %s: el cliente no tiene email.",
                reserva.pk,
            )
            return

        send_mail(
            subject=f"CasaLista: reserva #{reserva.pk} recibida",
            message=(
                f"Tu solicitud quedó en estado {reserva.estado}. "
                f"Total: ${reserva.total}."
            ),
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "no-reply@casalista.local",
            ),
            recipient_list=[destinatario],
            fail_silently=False,
        )
