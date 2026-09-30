from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comun.pruebas import NotificadorEspia, escenario_basico
from apps.reservas.dto import CrearReservaCommand, LineaSolicitada
from apps.reservas.models import Reserva
from apps.reservas.services import ReservaService

TOKEN = "token-de-prueba"


@override_settings(TOKEN_SERVICIO_PAGOS=TOKEN)
class ConfirmacionInternaAPITest(APITestCase):
    """El endpoint que llama el servicio de pagos (Flask) cuando aprueba un cobro."""

    def setUp(self):
        self.escenario = escenario_basico()
        self.reserva = ReservaService(notificador=NotificadorEspia()).crear_reserva(
            CrearReservaCommand(
                usuario_id=self.escenario["cliente"].usuario_id,
                bloque_id=self.escenario["bloque"].pk,
                direccion="Calle 33 #70-21",
                zona="Laureles",
                lineas=(
                    LineaSolicitada(servicio_id=self.escenario["servicio"].pk, cantidad=1),
                ),
            )
        )
        self.url = reverse("interno:confirmacion", args=[self.reserva.pk])

    def test_200_confirma_la_reserva_con_el_token_de_servicio(self):
        respuesta = self.client.post(self.url, HTTP_X_TOKEN_SERVICIO=TOKEN)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], Reserva.Estado.CONFIRMADA)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, Reserva.Estado.CONFIRMADA)

    def test_403_sin_token(self):
        respuesta = self.client.post(self.url)
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_403_con_token_equivocado(self):
        respuesta = self.client.post(self.url, HTTP_X_TOKEN_SERVICIO="otro")
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_403_un_cliente_no_puede_confirmarse_la_reserva_sin_pagar(self):
        self.client.force_authenticate(user=self.escenario["cliente"].usuario)

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, Reserva.Estado.PENDIENTE)

    @override_settings(TOKEN_SERVICIO_PAGOS="")
    def test_403_si_el_token_no_esta_configurado(self):
        respuesta = self.client.post(self.url, HTTP_X_TOKEN_SERVICIO="")
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_404_si_la_reserva_no_existe(self):
        respuesta = self.client.post(
            reverse("interno:confirmacion", args=[999999]),
            HTTP_X_TOKEN_SERVICIO=TOKEN,
        )

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(respuesta.data["error"]["codigo"], "RES-04")

    def test_409_si_la_reserva_ya_estaba_cancelada(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(
            estado=Reserva.Estado.CANCELADA
        )

        respuesta = self.client.post(self.url, HTTP_X_TOKEN_SERVICIO=TOKEN)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
