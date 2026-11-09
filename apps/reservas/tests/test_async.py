from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils.translation import override

from apps.comun.pruebas import escenario_basico
from apps.reservas.infraestructura.notificaciones import NotificadorAsincrono
from apps.reservas.models import NotificacionPendiente, Reserva
from apps.reservas.services import ReservaService
from apps.reservas.tasks import entregar_notificacion, publicar_notificacion, recuperar_notificaciones
from apps.reservas.tests.test_services import comando_de


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificacionAsincronaTest(TestCase):
    def setUp(self):
        self.escenario=escenario_basico()

    def crear(self):
        with override('en'):
            return ReservaService(notificador=NotificadorAsincrono()).crear_reserva(comando_de(self.escenario))

    @patch('apps.reservas.tasks.entregar_notificacion.delay')
    def test_publica_despues_de_commit_y_conserva_idioma(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            reserva=self.crear()
            delay.assert_not_called()
        evento=NotificacionPendiente.objects.get(reserva=reserva)
        self.assertEqual(evento.idioma,'en')
        delay.assert_called_once_with(evento.pk)

    @patch('apps.reservas.tasks.entregar_notificacion.delay')
    def test_rollback_no_publica_ni_deja_outbox(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.crear()
                    raise RuntimeError('rollback')
            except RuntimeError: pass
        self.assertEqual(Reserva.objects.count(),0)
        self.assertEqual(NotificacionPendiente.objects.count(),0)
        delay.assert_not_called()

    @patch('apps.reservas.tasks.entregar_notificacion.delay',side_effect=ConnectionError('Redis'))
    def test_caida_broker_conserva_reserva_y_evento(self, delay):
        with self.captureOnCommitCallbacks(execute=True): reserva=self.crear()
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())
        self.assertIsNone(NotificacionPendiente.objects.get(reserva=reserva).enviada_en)

    def test_worker_traduce_y_no_reenvia_un_evento_entregado(self):
        reserva=self.crear()
        evento=NotificacionPendiente.objects.get(reserva=reserva)
        self.assertEqual(entregar_notificacion.run(evento.pk),'entregada')
        self.assertEqual(entregar_notificacion.run(evento.pk),'ya_entregada')
        self.assertEqual(len(mail.outbox),1)
        self.assertIn('Booking',mail.outbox[0].subject)
        self.assertIn('Hello',mail.outbox[0].body)
        evento.refresh_from_db()
        self.assertIsNotNone(evento.enviada_en)

    @patch('apps.reservas.tasks.entregar_notificacion.retry',side_effect=RuntimeError('retry'))
    @patch('apps.reservas.tasks.NotificadorEmail.enviar_confirmacion_reserva',side_effect=OSError('SMTP'))
    def test_falla_smtp_reintenta_sin_marcar_entregada(self, enviar, retry):
        evento=NotificacionPendiente.objects.get(reserva=self.crear())
        with self.assertRaises(RuntimeError): entregar_notificacion.run(evento.pk)
        retry.assert_called_once()
        evento.refresh_from_db()
        self.assertIsNone(evento.enviada_en)

    @patch('apps.reservas.tasks.publicar_notificacion')
    def test_beat_recupera_eventos_pendientes(self, publicar):
        evento=NotificacionPendiente.objects.get(reserva=self.crear())
        recuperar_notificaciones.run()
        publicar.assert_called_once_with(evento.pk)
