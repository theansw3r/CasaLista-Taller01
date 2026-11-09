from django.utils.translation import gettext as _, gettext_lazy as _lazy
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.reservas.dominio.puertos import Notificador

logger = logging.getLogger(__name__)


def _asunto(reserva) -> str:
    return _("CasaLista - Reserva #%(id)s creada") % {"id": reserva.pk}


def _cuerpo(reserva) -> str:
    inicio = timezone.localtime(reserva.bloque.inicio)
    return _(
        "Hola %(cliente)s,\n\nTu reserva con %(profesional)s quedó registrada.\n"
        "Fecha: %(fecha)s\nDirección: %(direccion)s (%(zona)s)\n"
        "Total: COP %(total)s\nEstado: %(estado)s\n\nTe avisaremos cuando confirmemos el pago."
    ) % {"cliente": reserva.cliente.nombre, "profesional": reserva.profesional.nombre,
         "fecha": inicio.strftime("%d/%m/%Y %H:%M"), "direccion": reserva.direccion,
         "zona": reserva.zona, "total": reserva.total, "estado": reserva.get_estado_display()}


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
            raise ValueError(_("El cliente no tiene correo"))
        send_mail(
            subject=_asunto(reserva),
            message=_cuerpo(reserva),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )


class NotificadorAsincrono(Notificador):
    nombre = "ASYNC"

    def enviar_confirmacion_reserva(self, reserva):
        from django.db import transaction
        from django.utils.translation import get_language
        from apps.reservas.models import NotificacionPendiente
        from apps.reservas.tasks import publicar_notificacion
        evento, _ = NotificacionPendiente.objects.get_or_create(
            reserva=reserva, defaults={"idioma": get_language() or "es"},
        )
        transaction.on_commit(lambda: publicar_notificacion(evento.pk))
