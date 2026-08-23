"""Pruebas del nucleo compartido: dinero, manejo de errores y operacion."""

from decimal import Decimal

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comun.dominio.dinero import a_dinero, porcentaje_de
from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    ErrorDeDominio,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


class DineroTest(SimpleTestCase):
    def test_redondea_a_dos_decimales(self):
        self.assertEqual(a_dinero("10.005"), Decimal("10.01"))
        self.assertEqual(a_dinero("10.004"), Decimal("10.00"))

    def test_redondea_hacia_arriba_en_el_empate(self):
        """HALF_UP y no el redondeo bancario de Python: asi factura el negocio."""
        self.assertEqual(a_dinero("2.5"), Decimal("2.50"))
        self.assertEqual(a_dinero("0.125"), Decimal("0.13"))

    def test_calcula_una_comision(self):
        self.assertEqual(porcentaje_de(Decimal("140000"), Decimal("0.12")),
                         Decimal("16800.00"))


class ExcepcionesDeDominioTest(SimpleTestCase):
    def test_cada_familia_lleva_su_codigo_http(self):
        self.assertEqual(ReglaDeNegocioViolada().estado_http, 409)
        self.assertEqual(DatosInvalidos().estado_http, 400)
        self.assertEqual(RecursoNoEncontrado().estado_http, 404)

    def test_el_contexto_viaja_en_la_respuesta(self):
        error = ErrorDeDominio("Algo paso", bloque_id=7)
        self.assertEqual(
            error.como_diccionario(),
            {"codigo": "ERR-000", "mensaje": "Algo paso", "contexto": {"bloque_id": 7}},
        )

    def test_sin_contexto_no_se_agrega_la_clave(self):
        self.assertNotIn("contexto", ErrorDeDominio("Simple").como_diccionario())

    def test_usa_el_mensaje_por_defecto_si_no_se_da_uno(self):
        class ErrorConcreto(ErrorDeDominio):
            mensaje_por_defecto = "Mensaje de la clase."

        self.assertEqual(str(ErrorConcreto()), "Mensaje de la clase.")


class SaludAPITest(APITestCase):
    def test_200_y_sin_autenticacion(self):
        """El balanceador consulta este endpoint sin credenciales."""
        respuesta = self.client.get(reverse("salud"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["base_de_datos"], "ok")

    def test_devuelve_el_identificador_de_correlacion(self):
        respuesta = self.client.get(reverse("salud"))
        self.assertIsNotNone(respuesta.data["id_peticion"])

    def test_respeta_el_identificador_que_manda_el_gateway(self):
        respuesta = self.client.get(reverse("salud"), HTTP_X_REQUEST_ID="abc-123")

        self.assertEqual(respuesta.data["id_peticion"], "abc-123")
        self.assertEqual(respuesta.headers["X-Request-ID"], "abc-123")


class ContratoOpenAPITest(APITestCase):
    def test_el_esquema_se_publica(self):
        """Si el esquema deja de generarse, el Gateway se queda sin contrato."""
        respuesta = self.client.get(reverse("esquema"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
