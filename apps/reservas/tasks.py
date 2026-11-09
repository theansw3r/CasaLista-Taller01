"""Entrega al menos una vez; el outbox conserva eventos si Redis no está disponible."""
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone, translation

from apps.reservas.models import NotificacionPendiente
from apps.reservas.infraestructura.notificaciones import NotificadorEmail

logger = logging.getLogger(__name__)


def publicar_notificacion(evento_id):
    try:
        entregar_notificacion.delay(evento_id)
    except Exception:
        # No convertir una reserva ya confirmada por BD en un 500 por el broker.
        # Beat recupera el evento persistido cuando vuelve Redis.
        logger.warning("Notificación %s pendiente de publicación", evento_id)


@shared_task(bind=True, max_retries=5, acks_late=True)
def entregar_notificacion(self, evento_id):
    try:
        with transaction.atomic():
            evento = NotificacionPendiente.objects.select_for_update().get(pk=evento_id)
            if evento.enviada_en:
                return "ya_entregada"
            with translation.override(evento.idioma):
                NotificadorEmail().enviar_confirmacion_reserva(evento.reserva)
            evento.enviada_en = timezone.now()
            evento.save(update_fields=["enviada_en"])
        return "entregada"
    except Exception as error:
        logger.warning("No se pudo entregar notificación %s", evento_id)
        raise self.retry(exc=error, countdown=min(300, 2 ** (self.request.retries + 2)))


@shared_task
def recuperar_notificaciones():
    # Las duplicaciones de publicación son seguras después de enviada_en.
    pendientes = NotificacionPendiente.objects.filter(enviada_en__isnull=True)
    for evento_id in pendientes.order_by("pk").values_list("pk", flat=True)[:100]:
        publicar_notificacion(evento_id)
