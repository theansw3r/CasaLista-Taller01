from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils.translation import override

from apps.integraciones.dominio.clima import CondicionesClima
from apps.integraciones.dominio.excepciones import ProveedorNoDisponible
from apps.integraciones.dominio.puertos import ProveedorClima
from apps.integraciones.infraestructura.cache import ProveedorClimaEnCache
from apps.integraciones.infraestructura.open_meteo import OpenMeteoAdapter
from apps.integraciones.services import ConsultaClimaService

FABRICA = "apps.integraciones.api.views.crear_proveedor_clima"


def respuesta_valida() -> dict:
    return {
        "current": {
            "time": "2026-11-09T10:00",
            "temperature_2m": 22.5,
            "precipitation": 0.1,
        },
        "current_units": {"temperature_2m": "°C", "precipitation": "mm"},
    }


def condiciones(**cambios) -> CondicionesClima:
    datos = {
        "ciudad": "Medellín",
        "temperatura_c": 20.0,
        "precipitacion_mm": 0.0,
        "observado_en": "2026-11-09T10:00",
        "zona_horaria": "America/Bogota",
        "fuente": "Open-Meteo",
        "atribucion": "https://open-meteo.com/",
    }
    datos.update(cambios)
    return CondicionesClima(**datos)


class ProveedorFalso(ProveedorClima):
    def __init__(self, resultado=None, error=None):
        self.resultado = resultado
        self.error = error
        self.llamadas = 0

    def condiciones(self) -> CondicionesClima:
        self.llamadas += 1
        if self.error:
            raise self.error
        return self.resultado


class OpenMeteoAdapterTest(SimpleTestCase):
    def setUp(self):
        self.sesion = Mock()
        self.sesion.get.return_value.status_code = 200
        self.sesion.get.return_value.json.return_value = respuesta_valida()

    def condiciones(self):
        return OpenMeteoAdapter(self.sesion).condiciones()

    def test_traduce_el_contrato_externo_al_objeto_de_dominio(self):
        dato = self.condiciones()

        self.assertIsInstance(dato, CondicionesClima)
        self.assertEqual(dato.temperatura_c, 22.5)
        self.assertEqual(dato.precipitacion_mm, 0.1)
        self.assertEqual(dato.fuente, "Open-Meteo")

    def test_limita_el_tiempo_y_no_sigue_redirecciones(self):
        self.condiciones()

        kwargs = self.sesion.get.call_args.kwargs
        self.assertEqual(kwargs["timeout"], (2, 4))
        self.assertFalse(kwargs["allow_redirects"])

    def test_timeout_se_vuelve_proveedor_no_disponible(self):
        self.sesion.get.side_effect = requests.Timeout()

        with self.assertRaises(ProveedorNoDisponible):
            self.condiciones()

    def test_cuerpo_que_no_es_json(self):
        self.sesion.get.return_value.json.side_effect = ValueError("no json")

        with self.assertRaises(ProveedorNoDisponible):
            self.condiciones()

    def test_rechaza_esquemas_y_numeros_invalidos(self):
        invalidos = [
            [],
            {},
            {"current": {}},
            {**respuesta_valida(), "current_units": {}},
            {
                **respuesta_valida(),
                "current": {"temperature_2m": True, "precipitation": 0, "time": "x"},
            },
            {
                **respuesta_valida(),
                "current": {
                    "temperature_2m": float("nan"),
                    "precipitation": 0,
                    "time": "x",
                },
            },
            {
                **respuesta_valida(),
                "current": {"temperature_2m": 20, "precipitation": -1, "time": "x"},
            },
        ]
        for cuerpo in invalidos:
            with self.subTest(cuerpo=cuerpo):
                self.sesion.get.return_value.json.return_value = cuerpo
                with self.assertRaises(ProveedorNoDisponible):
                    self.condiciones()

    def test_no_acepta_errores_ni_redirecciones(self):
        for estado in [301, 429, 500]:
            with self.subTest(estado=estado):
                self.sesion.get.return_value.status_code = estado
                with self.assertRaises(ProveedorNoDisponible):
                    self.condiciones()


class ProveedorClimaEnCacheTest(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_segunda_consulta_sale_de_la_cache(self):
        real = ProveedorFalso(resultado=condiciones())
        proveedor = ProveedorClimaEnCache(real, clave="prueba", segundos=60)

        proveedor.condiciones()
        proveedor.condiciones()

        self.assertEqual(real.llamadas, 1)

    def test_no_guarda_fallos(self):
        real = ProveedorFalso(error=ProveedorNoDisponible())
        proveedor = ProveedorClimaEnCache(real, clave="prueba", segundos=60)

        for _intento in range(2):
            with self.assertRaises(ProveedorNoDisponible):
                proveedor.condiciones()

        self.assertEqual(real.llamadas, 2)


class ConsultaClimaServiceTest(SimpleTestCase):
    def test_usa_el_puerto_que_le_inyectan(self):
        esperado = condiciones(temperatura_c=18.0)

        resultado = ConsultaClimaService(ProveedorFalso(resultado=esperado)).consultar()

        self.assertEqual(resultado, esperado)


class ClimaApiTest(SimpleTestCase):
    url = reverse("integraciones:clima")

    @patch(FABRICA)
    def test_responde_el_contrato_publico(self, fabrica):
        fabrica.return_value = ProveedorFalso(resultado=condiciones())

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            set(respuesta.json()),
            {
                "ciudad",
                "temperatura_c",
                "precipitacion_mm",
                "observado_en",
                "zona_horaria",
                "fuente",
                "atribucion",
            },
        )

    @patch(FABRICA)
    def test_falla_externa_responde_503_traducido(self, fabrica):
        fabrica.return_value = ProveedorFalso(error=ProveedorNoDisponible())

        respuesta = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE="en")

        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()["error"]["codigo"], "INT-503")
        self.assertIn("Weather", respuesta.json()["error"]["mensaje"])


class AliadoApiTest(SimpleTestCase):
    def test_aliado_esta_pendiente_sin_inventar_datos(self):
        respuesta = self.client.get(
            reverse("integraciones:aliado"), HTTP_ACCEPT_LANGUAGE="en"
        )

        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()["error"]["codigo"], "ALIADO-PENDIENTE")
        self.assertIn("partner team", respuesta.json()["error"]["mensaje"])


class InterfazIdiomaTest(SimpleTestCase):
    def test_portada_y_catalogo_javascript_usan_el_idioma(self):
        en = self.client.get("/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(en, "More time for you.")
        self.assertContains(en, 'lang="en"')
        self.assertNotContains(en, "Datos de prueba:")

        js = self.client.get("/jsi18n/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(js, "My bookings")

        es = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(es, "Más tiempo para ti.")

    def test_cambio_de_idioma_guarda_la_preferencia(self):
        respuesta = self.client.post("/i18n/setlang/", {"language": "en", "next": "/"})

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.cookies["django_language"].value, "en")

    def test_mensaje_de_error_del_clima_esta_traducido(self):
        with override("en"):
            self.assertIn("Weather", str(ProveedorNoDisponible()))
