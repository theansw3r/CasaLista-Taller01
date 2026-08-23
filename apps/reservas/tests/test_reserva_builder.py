"""
Pruebas del Builder: una por invariante.

El Builder es el guardian de las reglas, asi que cada regla del Business Case
que le corresponde tiene su prueba. Todas siguen la misma forma: se prepara un
escenario que viola UNA regla y se comprueba que salta esa regla y no otra.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.comun.pruebas import (
    crear_bloque,
    crear_cliente,
    crear_profesional,
    crear_servicio,
    escenario_basico,
)
from apps.cuentas.dominio.excepciones import ProfesionalNoHabilitado
from apps.reservas.dominio.excepciones import (
    BloqueDeOtroProfesional,
    BloqueNoDisponible,
    CantidadInvalida,
    DatosDeReservaIncompletos,
    DuracionExcedeBloque,
    ReservaSinServicios,
    ServiciosDeDistintosProfesionales,
)
from apps.reservas.dominio.reserva_builder import ReservaBuilder
from apps.reservas.dominio.tarifas import TarifaDinamica
from apps.reservas.models import BloqueDisponibilidad, Reserva


class ReservaBuilderTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()

    def _builder(self, **cambios) -> ReservaBuilder:
        """Builder ya armado con un escenario valido, para tocar un solo dato."""
        datos = {**self.escenario, **cambios}
        builder = (
            ReservaBuilder()
            .para_cliente(datos["cliente"])
            .en_bloque(datos["bloque"])
            .en_direccion("Calle 33 #70-21", datos.get("zona", "Laureles"))
        )
        if datos.get("con_servicio", True):
            builder.agregar_servicio(datos["servicio"], datos.get("cantidad", 1))
        return builder

    # --- Camino feliz --------------------------------------------------
    def test_construye_la_reserva_y_ocupa_el_bloque(self):
        reserva = self._builder().build()

        self.assertEqual(reserva.estado, Reserva.Estado.PENDIENTE)
        self.assertEqual(reserva.total, Decimal("50000.00"))
        self.assertEqual(reserva.detalles.count(), 1)

        self.escenario["bloque"].refresh_from_db()
        self.assertEqual(
            self.escenario["bloque"].estado, BloqueDisponibilidad.Estado.OCUPADO
        )

    def test_congela_el_precio_del_servicio(self):
        """Si el precio cambia despues, la reserva conserva el que se acordo."""
        reserva = self._builder().build()
        servicio = self.escenario["servicio"]

        servicio.precio_base = Decimal("99999")
        servicio.save(update_fields=["precio_base"])

        detalle = reserva.detalles.first()
        self.assertEqual(detalle.precio_unitario, Decimal("50000.00"))
        self.assertEqual(reserva.total, Decimal("50000.00"))

    def test_el_profesional_se_deduce_de_los_servicios(self):
        reserva = self._builder().build()
        self.assertEqual(reserva.profesional_id, self.escenario["profesional"].pk)

    def test_usa_la_estrategia_de_tarifa_que_se_le_inyecte(self):
        """La misma reserva cuesta distinto segun la estrategia."""
        # Un sabado a las 20:00 dispara los dos recargos: 1 + 0.20 + 0.15.
        sabado = timezone.localtime() + timedelta(days=(5 - timezone.localtime().weekday()) % 7 + 7)
        inicio = sabado.replace(hour=20, minute=0, second=0, microsecond=0)
        bloque = BloqueDisponibilidad.objects.create(
            profesional=self.escenario["profesional"],
            inicio=inicio,
            fin=inicio + timedelta(hours=2),
        )

        reserva = (
            self._builder(bloque=bloque)
            .con_calculador_tarifa(TarifaDinamica())
            .build()
        )

        self.assertEqual(reserva.tarifa_aplicada, "DINAMICA")
        self.assertEqual(reserva.total, Decimal("67500.00"))  # 50000 * 1.35

    # --- Datos incompletos ---------------------------------------------
    def test_exige_cliente(self):
        builder = ReservaBuilder().en_bloque(self.escenario["bloque"])
        builder.agregar_servicio(self.escenario["servicio"])
        builder.en_direccion("Calle 33", "Laureles")
        with self.assertRaises(DatosDeReservaIncompletos):
            builder.build()

    def test_exige_direccion_y_zona(self):
        builder = self._builder()
        builder.en_direccion("", "")
        with self.assertRaises(DatosDeReservaIncompletos):
            builder.build()

    def test_exige_al_menos_un_servicio(self):
        with self.assertRaises(ReservaSinServicios):
            self._builder(con_servicio=False).build()

    def test_rechaza_cantidad_no_positiva(self):
        with self.assertRaises(CantidadInvalida):
            self._builder(cantidad=0).build()

    # --- Reglas del Business Case --------------------------------------
    def test_rn02_no_mezcla_servicios_de_dos_profesionales(self):
        otro = crear_profesional(nombre="Otro profesional")
        builder = self._builder()
        builder.agregar_servicio(crear_servicio(otro))

        with self.assertRaises(ServiciosDeDistintosProfesionales):
            builder.build()

    def test_rn07_rechaza_profesional_sin_verificar(self):
        profesional = crear_profesional(verificado=False)
        with self.assertRaises(ProfesionalNoHabilitado):
            self._builder(
                servicio=crear_servicio(profesional),
                bloque=crear_bloque(profesional),
            ).build()

    def test_rn07_rechaza_zona_no_cubierta(self):
        with self.assertRaises(ProfesionalNoHabilitado):
            self._builder(zona="Sabaneta").build()

    def test_rn01_rechaza_bloque_de_otro_profesional(self):
        otro = crear_profesional(nombre="Ajeno")
        with self.assertRaises(BloqueDeOtroProfesional):
            self._builder(bloque=crear_bloque(otro)).build()

    def test_rn01_rechaza_bloque_ya_ocupado(self):
        self._builder().build()

        segundo_cliente = crear_cliente(nombre="Segundo cliente")
        with self.assertRaises(BloqueNoDisponible):
            self._builder(cliente=segundo_cliente).build()

    def test_rn01_no_deja_reserva_a_medias_si_falla(self):
        """Una construccion fallida no debe dejar rastro en la base."""
        self._builder().build()
        reservas_antes = Reserva.objects.count()

        with self.assertRaises(BloqueNoDisponible):
            self._builder(cliente=crear_cliente()).build()

        self.assertEqual(Reserva.objects.count(), reservas_antes)

    def test_rechaza_servicios_que_no_caben_en_la_franja(self):
        largo = crear_servicio(self.escenario["profesional"], minutos=180)
        with self.assertRaises(DuracionExcedeBloque) as capturado:
            self._builder(servicio=largo).build()

        # El contexto del error le dice al cliente exactamente que sobro.
        self.assertEqual(capturado.exception.contexto["minutos_solicitados"], 180)
        self.assertEqual(capturado.exception.contexto["minutos_disponibles"], 120)

    def test_previsualizar_no_guarda_nada(self):
        total = self._builder().previsualizar_total()

        self.assertEqual(total, Decimal("50000.00"))
        self.assertEqual(Reserva.objects.count(), 0)
