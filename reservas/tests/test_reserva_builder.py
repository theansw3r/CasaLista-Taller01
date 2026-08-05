"""El Builder es el guardian de las invariantes: si algo falla, no se guarda nada."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from ..domain.excepciones import (
    BloqueDeOtroProfesional,
    BloqueNoDisponible,
    CantidadInvalida,
    DatosIncompletos,
    DuracionExcedeBloque,
    ProfesionalNoHabilitado,
    ReservaSinServicios,
    ServicioInactivo,
    ServiciosDeDistintosProfesionales,
)
from ..domain.reserva_builder import ReservaBuilder
from ..domain.tarifas import TarifaDinamica
from ..models import BloqueDisponibilidad, Reserva
from .factoria_de_datos import (
    crear_bloque,
    crear_cliente,
    crear_profesional,
    crear_servicio,
)


class ReservaBuilderTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.bloque = crear_bloque(self.profesional)

    def _builder(self):
        return (
            ReservaBuilder()
            .para_cliente(self.cliente)
            .en_bloque(self.bloque)
            .en_direccion("Calle 30 #45-12", "Laureles")
            .agregar_servicio(self.servicio, 1)
        )

    # --- camino feliz ----------------------------------------------------
    def test_construye_una_reserva_valida_y_ocupa_el_bloque(self):
        reserva = self._builder().build()

        self.assertEqual(reserva.estado, Reserva.Estado.PENDIENTE)
        self.assertEqual(reserva.total, Decimal("80000.00"))
        self.assertEqual(reserva.detalles.count(), 1)
        self.bloque.refresh_from_db()
        self.assertEqual(self.bloque.estado, BloqueDisponibilidad.Estado.OCUPADO)

    def test_congela_el_precio_del_servicio_en_la_linea(self):
        reserva = self._builder().build()
        self.servicio.precio_base = Decimal("120000")
        self.servicio.save()

        detalle = reserva.detalles.get()
        self.assertEqual(detalle.precio_unitario, Decimal("80000.00"))

    def test_los_pasos_son_encadenables_en_cualquier_orden(self):
        reserva = (
            ReservaBuilder()
            .agregar_servicio(self.servicio, 2)
            .en_direccion("Calle 30 #45-12", "Laureles")
            .en_bloque(self.bloque)
            .para_cliente(self.cliente)
            .build()
        )
        self.assertEqual(reserva.total, Decimal("160000.00"))

    def test_usa_la_estrategia_de_tarifa_inyectada(self):
        sabado = timezone.localtime(timezone.now()).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
        while sabado.weekday() != 5:
            sabado += timedelta(days=1)
        bloque_nocturno = crear_bloque(self.profesional, inicio=sabado)

        reserva = (
            ReservaBuilder()
            .para_cliente(self.cliente)
            .en_bloque(bloque_nocturno)
            .en_direccion("Calle 30 #45-12", "Laureles")
            .agregar_servicio(self.servicio, 1)
            .con_calculador_tarifa(TarifaDinamica())
            .build()
        )

        # 80.000 * (1 + 0.20 nocturno + 0.15 fin de semana)
        self.assertEqual(reserva.total, Decimal("108000.00"))
        self.assertEqual(reserva.tarifa_aplicada, "DINAMICA")

    # --- invariantes -----------------------------------------------------
    def test_rechaza_reserva_sin_servicios(self):
        constructor = (
            ReservaBuilder()
            .para_cliente(self.cliente)
            .en_bloque(self.bloque)
            .en_direccion("Calle 30", "Laureles")
        )
        with self.assertRaises(ReservaSinServicios):
            constructor.build()

    def test_rechaza_cliente_faltante(self):
        constructor = (
            ReservaBuilder()
            .en_bloque(self.bloque)
            .en_direccion("Calle 30", "Laureles")
            .agregar_servicio(self.servicio)
        )
        with self.assertRaises(DatosIncompletos):
            constructor.build()

    def test_rechaza_cantidad_no_positiva(self):
        with self.assertRaises(CantidadInvalida):
            self._builder().agregar_servicio(self.servicio, 0).build()

    def test_rechaza_servicio_inactivo(self):
        inactivo = crear_servicio(self.profesional, nombre="Pintura", activo=False)
        constructor = (
            ReservaBuilder()
            .para_cliente(self.cliente)
            .en_bloque(self.bloque)
            .en_direccion("Calle 30", "Laureles")
            .agregar_servicio(inactivo)
        )
        with self.assertRaises(ServicioInactivo):
            constructor.build()

    def test_rn02_rechaza_servicios_de_distintos_profesionales(self):
        otro = crear_profesional(nombre="Luis Electricista", email="luis@casalista.co")
        ajeno = crear_servicio(otro, nombre="Cambio de toma")

        with self.assertRaises(ServiciosDeDistintosProfesionales):
            self._builder().agregar_servicio(ajeno).build()

    def test_rn07_rechaza_profesional_no_verificado(self):
        self.profesional.verificado = False
        self.profesional.save()

        with self.assertRaises(ProfesionalNoHabilitado):
            self._builder().build()

    def test_rn07_rechaza_zona_fuera_de_cobertura(self):
        constructor = self._builder().en_direccion("Calle 1", "Sabaneta")
        with self.assertRaises(ProfesionalNoHabilitado):
            constructor.build()

    def test_rn01_rechaza_bloque_ya_ocupado(self):
        self._builder().build()

        with self.assertRaises(BloqueNoDisponible):
            self._builder().build()

    def test_rn01_rechaza_bloque_de_otro_profesional(self):
        otro = crear_profesional(nombre="Luis Electricista", email="luis@casalista.co")
        bloque_ajeno = crear_bloque(otro)

        with self.assertRaises(BloqueDeOtroProfesional):
            self._builder().en_bloque(bloque_ajeno).build()

    def test_rn08_rechaza_servicios_que_no_caben_en_el_bloque(self):
        largo = crear_servicio(self.profesional, nombre="Reforma", duracion=180)
        constructor = (
            ReservaBuilder()
            .para_cliente(self.cliente)
            .en_bloque(self.bloque)  # dura 120 minutos
            .en_direccion("Calle 30", "Laureles")
            .agregar_servicio(largo)
        )
        with self.assertRaises(DuracionExcedeBloque):
            constructor.build()

    def test_una_construccion_invalida_no_deja_rastro_en_la_base(self):
        with self.assertRaises(ProfesionalNoHabilitado):
            self._builder().en_direccion("Calle 1", "Sabaneta").build()

        self.assertEqual(Reserva.objects.count(), 0)
        self.bloque.refresh_from_db()
        self.assertTrue(self.bloque.esta_libre())
