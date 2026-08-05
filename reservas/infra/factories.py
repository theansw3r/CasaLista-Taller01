import os

from django.core.exceptions import ImproperlyConfigured

from reservas.infra.notifiers import (
    ConsolaNotificador,
    EmailNotificador,
    NotificadorReserva,
)


class NotificadorFactory:
    @staticmethod
    def crear() -> NotificadorReserva:
        backend = os.getenv("NOTIFICATION_BACKEND", "CONSOLE").upper()

        if backend == "CONSOLE":
            return ConsolaNotificador()
        if backend == "EMAIL":
            return EmailNotificador()

        raise ImproperlyConfigured(
            "NOTIFICATION_BACKEND debe ser CONSOLE o EMAIL."
        )
