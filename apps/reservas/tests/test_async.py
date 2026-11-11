from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils.translation import override

from apps.comun.pruebas import escenario_basico
from apps.reservas.infraestructura.notificaciones import (
    NotificadorAsincrono,
    NotificadorConsola,
    NotificadorEmail,
)
from apps.reservas.models import NotificacionPendiente, Reserva
from apps.reservas.services import ReservaService
from apps.reservas.tasks import entregar_notificacion, recuperar_notificaciones
from apps.reservas.tests.test_services import comando_de

CORREO_EN_MEMORIA = "django.core.mail.backends.locmem.EmailBackend"


class SimularRollback(Exception):
    pass


@override_settings(EMAIL_BACKEND=CORREO_EN_MEMORIA)
class NotificacionAsincronaTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()

    def crear(self):
        with override("en"):
            servicio = ReservaService(notificador=NotificadorAsincrono())
            return servicio.crear_reserva(comando_de(self.escenario))

    @patch("apps.reservas.tasks.entregar_notificacion.delay")
    def test_publica_despues_de_commit_y_conserva_idioma(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            reserva = self.crear()
            delay.assert_not_called()

        evento = NotificacionPendiente.objects.get(reserva=reserva)
        self.assertEqual(evento.idioma, "en")
        delay.assert_called_once_with(evento.pk)

    @patch("apps.reservas.tasks.entregar_notificacion.delay")
    def test_rollback_no_publica_ni_deja_outbox(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(SimularRollback):
                with transaction.atomic():
                    self.crear()
                    raise SimularRollback

        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(NotificacionPendiente.objects.count(), 0)
        delay.assert_not_called()

    @patch(
        "apps.reservas.tasks.entregar_notificacion.delay",
        side_effect=ConnectionError("Redis"),
    )
    def test_caida_broker_conserva_reserva_y_evento(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            reserva = self.crear()

        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())
        self.assertIsNone(NotificacionPendiente.objects.get(reserva=reserva).enviada_en)

    def test_worker_traduce_y_no_reenvia_un_evento_entregado(self):
        evento = NotificacionPendiente.objects.get(reserva=self.crear())

        self.assertEqual(entregar_notificacion.run(evento.pk), "entregada")
        self.assertEqual(entregar_notificacion.run(evento.pk), "ya_entregada")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Booking", mail.outbox[0].subject)
        self.assertIn("Hello", mail.outbox[0].body)
        evento.refresh_from_db()
        self.assertIsNotNone(evento.enviada_en)

    @patch(
        "apps.reservas.tasks.entregar_notificacion.retry",
        side_effect=RuntimeError("retry"),
    )
    @patch(
        "apps.reservas.tasks.enviar_correo_confirmacion",
        side_effect=OSError("SMTP"),
    )
    def test_falla_smtp_reintenta_sin_marcar_entregada(self, enviar, retry):
        evento = NotificacionPendiente.objects.get(reserva=self.crear())

        with self.assertRaises(RuntimeError):
            entregar_notificacion.run(evento.pk)

        retry.assert_called_once()
        evento.refresh_from_db()
        self.assertIsNone(evento.enviada_en)

    @patch("apps.reservas.tasks.publicar_notificacion")
    def test_beat_recupera_eventos_pendientes(self, publicar):
        evento = NotificacionPendiente.objects.get(reserva=self.crear())

        recuperar_notificaciones.run()

        publicar.assert_called_once_with(evento.pk)


@override_settings(EMAIL_BACKEND=CORREO_EN_MEMORIA)
class NotificacionSincronaTest(TestCase):
    """MOCK y REAL actuan despues del COMMIT, nunca dentro de la transaccion."""

    def setUp(self):
        self.escenario = escenario_basico()

    def crear(self, notificador):
        servicio = ReservaService(notificador=notificador)
        return servicio.crear_reserva(comando_de(self.escenario))

    def test_correo_sale_solo_despues_del_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.crear(NotificadorEmail())
            self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(len(mail.outbox), 1)

    @patch(
        "apps.reservas.infraestructura.notificaciones.send_mail",
        side_effect=OSError("SMTP caido"),
    )
    def test_falla_del_correo_no_deshace_la_reserva(self, send_mail):
        with self.captureOnCommitCallbacks(execute=True):
            reserva = self.crear(NotificadorEmail())

        send_mail.assert_called_once()
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())

    def test_rollback_no_avisa_de_una_reserva_que_no_existe(self):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(SimularRollback):
                with transaction.atomic():
                    self.crear(NotificadorEmail())
                    raise SimularRollback

        self.assertEqual(len(mail.outbox), 0)

    def test_consola_registra_despues_del_commit(self):
        logger = "apps.reservas.infraestructura.notificaciones"
        with self.assertLogs(logger, level="INFO") as registro:
            with self.captureOnCommitCallbacks(execute=True):
                self.crear(NotificadorConsola())

        self.assertIn("[MOCK]", registro.output[0])
