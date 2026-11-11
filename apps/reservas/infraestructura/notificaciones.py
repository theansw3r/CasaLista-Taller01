"""Adaptadores del puerto Notificador.

ReservaService llama al notificador dentro de la transaccion que crea la
reserva. Cada adaptador decide cuando actuar:

- MOCK y REAL esperan al COMMIT: no se avisa de una reserva que luego se
  deshace, y un fallo del correo no tumba una reserva que ya quedo guardada.
- ASYNC escribe el evento (outbox) en esa misma transaccion y lo publica en
  Redis despues del COMMIT. Si la reserva se deshace, el evento tambien.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from apps.reservas.dominio.puertos import Notificador
from apps.reservas.models import NotificacionPendiente

logger = logging.getLogger(__name__)


class SinDestinatario(Exception):
    """El cliente no tiene correo registrado."""


def _asunto(reserva) -> str:
    return _("CasaLista - Reserva #%(id)s creada") % {"id": reserva.pk}


def _cuerpo(reserva) -> str:
    inicio = timezone.localtime(reserva.bloque.inicio)
    return _(
        "Hola %(cliente)s,\n\nTu reserva con %(profesional)s quedó registrada.\n"
        "Fecha: %(fecha)s\nDirección: %(direccion)s (%(zona)s)\n"
        "Total: COP %(total)s\nEstado: %(estado)s\n\nTe avisaremos cuando confirmemos el pago."
    ) % {
        "cliente": reserva.cliente.nombre,
        "profesional": reserva.profesional.nombre,
        "fecha": inicio.strftime("%d/%m/%Y %H:%M"),
        "direccion": reserva.direccion,
        "zona": reserva.zona,
        "total": reserva.total,
        "estado": reserva.get_estado_display(),
    }


def enviar_correo_confirmacion(reserva) -> None:
    """Envia el correo y deja subir cualquier error.

    La usa el worker de Celery, que necesita enterarse del fallo para
    reintentar y no marcar el evento como entregado.
    """
    destinatario = getattr(reserva.cliente.usuario, "email", "")
    if not destinatario:
        raise SinDestinatario(reserva.pk)
    send_mail(
        subject=_asunto(reserva),
        message=_cuerpo(reserva),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[destinatario],
        fail_silently=False,
    )


class NotificadorConsola(Notificador):
    nombre = "MOCK"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        transaction.on_commit(lambda: self._registrar(reserva))

    @staticmethod
    def _registrar(reserva) -> None:
        logger.info("[MOCK] %s | %s", _asunto(reserva), reserva.cliente.nombre)


class NotificadorEmail(Notificador):
    nombre = "REAL"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        transaction.on_commit(lambda: self._enviar_sin_afectar_la_reserva(reserva))

    @staticmethod
    def _enviar_sin_afectar_la_reserva(reserva) -> None:
        # La reserva ya esta guardada: si el correo falla se registra, pero el
        # cliente no recibe un error por algo que si se hizo. Quien necesite
        # reintentos usa ASYNC.
        try:
            enviar_correo_confirmacion(reserva)
        except Exception:
            logger.exception("Reserva %s: no se pudo enviar el correo.", reserva.pk)


class NotificadorAsincrono(Notificador):
    nombre = "ASYNC"

    def enviar_confirmacion_reserva(self, reserva) -> None:
        # Import diferido: tasks importa este modulo para enviar el correo.
        from apps.reservas.tasks import publicar_notificacion

        evento, _creado = NotificacionPendiente.objects.get_or_create(
            reserva=reserva,
            defaults={"idioma": get_language() or settings.LANGUAGE_CODE},
        )
        transaction.on_commit(lambda: publicar_notificacion(evento.pk))
