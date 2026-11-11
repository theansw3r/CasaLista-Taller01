"""Tareas de Celery para las notificaciones de reserva.

Entrega al menos una vez: el evento vive en Postgres (outbox) antes de llegar
a Redis, asi que una caida del broker no lo pierde. Beat lo vuelve a publicar.
"""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone, translation

from apps.reservas.infraestructura.notificaciones import enviar_correo_confirmacion
from apps.reservas.models import NotificacionPendiente

logger = logging.getLogger(__name__)

MAX_REINTENTOS = 5
ESPERA_MAXIMA_SEGUNDOS = 300
EVENTOS_POR_CICLO = 100


def publicar_notificacion(evento_id: int) -> None:
    try:
        entregar_notificacion.delay(evento_id)
    except Exception:
        # La reserva ya quedo guardada: una caida del broker no puede volverla
        # un 500. El evento sigue pendiente en la base y Beat lo recupera.
        logger.warning("Notificación %s pendiente de publicación", evento_id)


@shared_task(bind=True, max_retries=MAX_REINTENTOS, acks_late=True)
def entregar_notificacion(self, evento_id: int) -> str:
    try:
        with transaction.atomic():
            evento = NotificacionPendiente.objects.select_for_update().get(pk=evento_id)
            if evento.enviada_en:
                return "ya_entregada"
            with translation.override(evento.idioma):
                enviar_correo_confirmacion(evento.reserva)
            evento.enviada_en = timezone.now()
            evento.save(update_fields=["enviada_en"])
        return "entregada"
    except Exception as error:
        logger.warning("No se pudo entregar notificación %s", evento_id)
        espera = min(ESPERA_MAXIMA_SEGUNDOS, 2 ** (self.request.retries + 2))
        raise self.retry(exc=error, countdown=espera) from error


@shared_task
def recuperar_notificaciones() -> None:
    # Publicar dos veces el mismo evento es seguro: el worker revisa enviada_en.
    pendientes = (
        NotificacionPendiente.objects.filter(enviada_en__isnull=True)
        .order_by("pk")
        .values_list("pk", flat=True)[:EVENTOS_POR_CICLO]
    )
    for evento_id in pendientes:
        publicar_notificacion(evento_id)
