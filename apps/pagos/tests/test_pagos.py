"""
Pruebas del modulo Pagos.

El caso interesante es RN-03: pagar tiene que dejar la reserva CONFIRMADA, y
si el pago no se aprueba la reserva no se puede mover de PENDIENTE.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comun.dominio.excepciones import AccesoNoAutorizado
from apps.comun.pruebas import (
    NotificadorEspia,
    PasarelaQueAprueba,
    PasarelaQueRechaza,
    crear_cliente,
    escenario_basico,
)
from apps.pagos.dominio.excepciones import (
    PagoRechazado,
    ReservaNoCobrable,
    ReservaYaPagada,
)
from apps.pagos.dto import ProcesarPagoCommand
from apps.pagos.models import Pago
from apps.pagos.services import PagoService
from apps.reservas.dto import CrearReservaCommand, LineaSolicitada
from apps.reservas.models import Reserva
from apps.reservas.services import ReservaService


def crear_reserva_de_prueba(escenario) -> Reserva:
    return ReservaService(notificador=NotificadorEspia()).crear_reserva(
        CrearReservaCommand(
            usuario_id=escenario["cliente"].usuario_id,
            bloque_id=escenario["bloque"].pk,
            direccion="Calle 33 #70-21",
            zona="Laureles",
            lineas=(LineaSolicitada(servicio_id=escenario["servicio"].pk, cantidad=1),),
        )
    )


class PagoServiceTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.reserva = crear_reserva_de_prueba(self.escenario)
        self.comando = ProcesarPagoCommand(
            usuario_id=self.escenario["cliente"].usuario_id,
            reserva_id=self.reserva.pk,
            medio=Pago.Medio.TARJETA,
        )

    def test_rn03_un_pago_aprobado_confirma_la_reserva(self):
        pago = PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)

        self.reserva.refresh_from_db()
        self.assertEqual(pago.estado, Pago.Estado.APROBADO)
        self.assertEqual(pago.referencia_externa, "REF-PRUEBA-001")
        self.assertEqual(self.reserva.estado, Reserva.Estado.CONFIRMADA)

    def test_el_monto_se_copia_del_total_de_la_reserva(self):
        pago = PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)
        self.assertEqual(pago.monto, Decimal("50000.00"))

    def test_rn03_un_rechazo_deja_la_reserva_pendiente(self):
        with self.assertRaises(PagoRechazado):
            PagoService(pasarela=PasarelaQueRechaza()).procesar(self.comando)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, Reserva.Estado.PENDIENTE)

    def test_un_rechazo_si_queda_registrado(self):
        """Un pago rechazado es informacion de negocio, no un no-evento."""
        with self.assertRaises(PagoRechazado):
            PagoService(pasarela=PasarelaQueRechaza()).procesar(self.comando)

        pago = Pago.objects.get(reserva=self.reserva)
        self.assertEqual(pago.estado, Pago.Estado.RECHAZADO)
        self.assertEqual(pago.motivo_rechazo, "Fondos insuficientes.")

    def test_no_se_puede_pagar_dos_veces(self):
        PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)

        with self.assertRaises(ReservaNoCobrable):
            PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)

    def test_no_se_puede_pagar_una_reserva_cancelada(self):
        self.reserva.estado = Reserva.Estado.CANCELADA
        self.reserva.save(update_fields=["estado"])

        with self.assertRaises(ReservaNoCobrable):
            PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)

    def test_no_se_puede_pagar_la_reserva_de_otro(self):
        intruso = crear_cliente(nombre="Intruso")
        ajeno = ProcesarPagoCommand(
            usuario_id=intruso.usuario_id,
            reserva_id=self.reserva.pk,
            medio=Pago.Medio.PSE,
        )
        with self.assertRaises(AccesoNoAutorizado):
            PagoService(pasarela=PasarelaQueAprueba()).procesar(ajeno)

    def test_un_reintento_tras_rechazo_choca_con_el_pago_ya_registrado(self):
        """Limitacion conocida: la relacion es 1 a 1, un rechazo bloquea el reintento.

        Se documenta como deuda tecnica en la wiki: el modelo del diagrama dice
        0..1 pagos por reserva, asi que reintentar exigira modelar intentos
        aparte en la Entrega 2.
        """
        with self.assertRaises(PagoRechazado):
            PagoService(pasarela=PasarelaQueRechaza()).procesar(self.comando)

        with self.assertRaises(ReservaYaPagada):
            PagoService(pasarela=PasarelaQueAprueba()).procesar(self.comando)


class PagoAPITest(APITestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.reserva = crear_reserva_de_prueba(self.escenario)
        self.client.force_authenticate(user=self.escenario["cliente"].usuario)
        self.url = reverse("pagos:procesar")

    def test_201_pago_aprobado(self):
        respuesta = self.client.post(
            self.url,
            {"reserva_id": self.reserva.pk, "medio": "TARJETA"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado"], Pago.Estado.APROBADO)
        self.assertEqual(respuesta.data["estado_reserva"], Reserva.Estado.CONFIRMADA)

    def test_400_si_el_medio_no_existe(self):
        respuesta = self.client.post(
            self.url,
            {"reserva_id": self.reserva.pk, "medio": "TRUEQUE"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_404_si_la_reserva_no_existe(self):
        respuesta = self.client.post(
            self.url, {"reserva_id": 999999, "medio": "PSE"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_409_si_la_reserva_ya_esta_pagada(self):
        cuerpo = {"reserva_id": self.reserva.pk, "medio": "PSE"}
        self.client.post(self.url, cuerpo, format="json")

        respuesta = self.client.post(self.url, cuerpo, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "PAG-03")

    def test_200_consulta_del_pago_propio(self):
        pago_id = self.client.post(
            self.url,
            {"reserva_id": self.reserva.pk, "medio": "TARJETA"},
            format="json",
        ).data["id"]

        respuesta = self.client.get(reverse("pagos:detalle", args=[pago_id]))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["id"], pago_id)

    def test_403_al_consultar_el_pago_de_otro(self):
        pago_id = self.client.post(
            self.url,
            {"reserva_id": self.reserva.pk, "medio": "TARJETA"},
            format="json",
        ).data["id"]

        self.client.force_authenticate(user=crear_cliente(nombre="Intruso").usuario)
        respuesta = self.client.get(reverse("pagos:detalle", args=[pago_id]))

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
