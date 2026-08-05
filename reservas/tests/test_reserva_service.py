"""El Service orquesta; las dependencias entran por el constructor."""

from decimal import Decimal

from django.test import TestCase, override_settings

from ..domain.excepciones import ClienteNoRegistrado, RecursoInexistente
from ..domain.tarifas import TarifaDinamica
from ..dto import CrearReservaCommand, LineaSolicitada
from ..models import Reserva
from ..services import ReservaService
from .factoria_de_datos import (
    NotificadorEspia,
    crear_bloque,
    crear_cliente,
    crear_profesional,
    crear_servicio,
)


class ReservaServiceTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.bloque = crear_bloque(self.profesional)
        self.espia = NotificadorEspia()

    def _comando(self, **cambios):
        base = {
            "usuario_id": self.cliente.usuario_id,
            "bloque_id": self.bloque.pk,
            "direccion": "Calle 30 #45-12",
            "zona": "Laureles",
            "lineas": (LineaSolicitada(servicio_id=self.servicio.pk, cantidad=1),),
        }
        base.update(cambios)
        return CrearReservaCommand(**base)

    def test_crea_la_reserva_y_notifica_una_sola_vez(self):
        servicio = ReservaService(notificador=self.espia)

        reserva = servicio.crear_reserva(self._comando())

        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(self.espia.enviados, [reserva])

    def test_usa_el_calculador_inyectado_por_encima_de_la_factory(self):
        servicio = ReservaService(
            notificador=self.espia, calculador_tarifa=TarifaDinamica()
        )

        reserva = servicio.crear_reserva(self._comando())

        self.assertEqual(reserva.tarifa_aplicada, "DINAMICA")

    @override_settings(NOTIFICADOR_TYPE="MOCK", TARIFA_TYPE="BASE")
    def test_sin_inyeccion_toma_las_implementaciones_del_entorno(self):
        servicio = ReservaService()

        self.assertEqual(servicio.notificador.nombre, "MOCK")
        self.assertEqual(servicio.calculador_tarifa.nombre, "BASE")

    def test_traduce_un_bloque_inexistente_a_error_de_dominio(self):
        servicio = ReservaService(notificador=self.espia)

        with self.assertRaises(RecursoInexistente):
            servicio.crear_reserva(self._comando(bloque_id=99999))

    def test_traduce_un_servicio_inexistente_a_error_de_dominio(self):
        servicio = ReservaService(notificador=self.espia)
        comando = self._comando(lineas=(LineaSolicitada(servicio_id=99999, cantidad=1),))

        with self.assertRaises(RecursoInexistente):
            servicio.crear_reserva(comando)

    def test_rechaza_a_un_usuario_sin_perfil_de_cliente(self):
        servicio = ReservaService(notificador=self.espia)
        comando = self._comando(usuario_id=self.profesional.usuario_id)

        with self.assertRaises(ClienteNoRegistrado):
            servicio.crear_reserva(comando)

    def test_no_notifica_cuando_la_reserva_es_invalida(self):
        servicio = ReservaService(notificador=self.espia)

        with self.assertRaises(Exception):
            servicio.crear_reserva(self._comando(zona="Sabaneta"))

        self.assertEqual(self.espia.enviados, [])
        self.assertEqual(Reserva.objects.count(), 0)

    def test_suma_varias_lineas_del_mismo_profesional(self):
        segundo = crear_servicio(
            self.profesional, nombre="Cambio de sifon", precio="45000", duracion=30
        )
        servicio = ReservaService(notificador=self.espia)
        comando = self._comando(
            lineas=(
                LineaSolicitada(servicio_id=self.servicio.pk, cantidad=1),
                LineaSolicitada(servicio_id=segundo.pk, cantidad=2),
            )
        )

        reserva = servicio.crear_reserva(comando)

        self.assertEqual(reserva.total, Decimal("170000.00"))
        self.assertEqual(reserva.detalles.count(), 2)
