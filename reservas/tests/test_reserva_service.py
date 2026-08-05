from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from reservas.domain.exceptions import (
    BloqueNoDisponible,
    ServiciosInvalidos,
)
from reservas.infra.factories import NotificadorFactory
from reservas.infra.notifiers import ConsolaNotificador, EmailNotificador
from reservas.models import (
    BloqueDisponibilidad,
    DetalleReserva,
    Profesional,
    Reserva,
    Servicio,
)
from reservas.services import ReservaService


class SpyNotificador:
    def __init__(self) -> None:
        self.reservas: list[int] = []

    def enviar_reserva_creada(self, reserva: Reserva) -> None:
        self.reservas.append(reserva.pk)


class ReservaServiceTests(TestCase):
    def setUp(self) -> None:
        self.cliente = get_user_model().objects.create_user(
            username="cliente",
            email="cliente@example.com",
            password="segura123",
        )
        self.profesional = Profesional.objects.create(
            nombre="Ana Técnica",
            email="ana@example.com",
            verificado=True,
        )
        ahora = timezone.now()
        self.bloque = BloqueDisponibilidad.objects.create(
            profesional=self.profesional,
            inicio=ahora + timedelta(days=1),
            fin=ahora + timedelta(days=1, hours=2),
        )
        self.servicio = Servicio.objects.create(
            profesional=self.profesional,
            nombre="Revisión eléctrica",
            precio_base=Decimal("80000.00"),
            duracion_minutos=120,
        )
        self.notificador = SpyNotificador()
        self.service = ReservaService(notificador=self.notificador)

    def test_crea_reserva_ocupa_bloque_y_notifica(self) -> None:
        datos = {
            "bloque_id": self.bloque.pk,
            "servicios": [
                {"servicio_id": self.servicio.pk, "cantidad": 2},
            ],
        }

        with self.captureOnCommitCallbacks(execute=True):
            reserva = self.service.crear_reserva(
                cliente=self.cliente,
                datos=datos,
            )

        self.bloque.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.PENDIENTE)
        self.assertEqual(reserva.total, Decimal("160000.00"))
        self.assertEqual(self.bloque.estado, BloqueDisponibilidad.Estado.OCUPADO)
        self.assertEqual(DetalleReserva.objects.filter(reserva=reserva).count(), 1)
        self.assertEqual(self.notificador.reservas, [reserva.pk])

    def test_rechaza_bloque_ocupado(self) -> None:
        self.bloque.estado = BloqueDisponibilidad.Estado.OCUPADO
        self.bloque.save(update_fields=["estado"])

        with self.assertRaises(BloqueNoDisponible):
            self.service.crear_reserva(
                cliente=self.cliente,
                datos={
                    "bloque_id": self.bloque.pk,
                    "servicios": [
                        {"servicio_id": self.servicio.pk, "cantidad": 1}
                    ],
                },
            )

    def test_rechaza_servicio_de_otro_profesional(self) -> None:
        otro = Profesional.objects.create(
            nombre="Otro profesional",
            email="otro@example.com",
            verificado=True,
        )
        servicio_ajeno = Servicio.objects.create(
            profesional=otro,
            nombre="Pintura",
            precio_base=Decimal("50000.00"),
            duracion_minutos=60,
        )

        with self.assertRaises(ServiciosInvalidos):
            self.service.crear_reserva(
                cliente=self.cliente,
                datos={
                    "bloque_id": self.bloque.pk,
                    "servicios": [
                        {"servicio_id": servicio_ajeno.pk, "cantidad": 1}
                    ],
                },
            )


class NotificadorFactoryTests(SimpleTestCase):
    @patch.dict("os.environ", {"NOTIFICATION_BACKEND": "CONSOLE"}, clear=False)
    def test_crea_notificador_de_consola(self) -> None:
        self.assertIsInstance(NotificadorFactory.crear(), ConsolaNotificador)

    @patch.dict("os.environ", {"NOTIFICATION_BACKEND": "EMAIL"}, clear=False)
    def test_crea_notificador_email(self) -> None:
        self.assertIsInstance(NotificadorFactory.crear(), EmailNotificador)
