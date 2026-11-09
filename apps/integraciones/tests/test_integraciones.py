from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.integraciones.adaptadores import OpenMeteoAdapter, ProveedorNoDisponible
from apps.integraciones.services import ConsultaClimaService


def respuesta_valida():
    return {"current": {"time": "2026-11-09T10:00", "temperature_2m": 22.5, "precipitation": 0.1},
            "current_units": {"temperature_2m": "°C", "precipitation": "mm"}}


class IntegracionesTest(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.sesion = Mock()
        self.sesion.get.return_value.status_code = 200
        self.sesion.get.return_value.json.return_value = respuesta_valida()

    def test_adapter_traduce_contrato_y_limita_tiempo(self):
        dato = OpenMeteoAdapter(self.sesion).condiciones()
        self.assertEqual(dato['temperatura_c'], 22.5)
        self.assertEqual(dato['fuente'], 'Open-Meteo')
        kwargs = self.sesion.get.call_args.kwargs
        self.assertEqual(kwargs['timeout'], (2, 4))
        self.assertFalse(kwargs['allow_redirects'])

    def test_timeout_no_impide_flujo_principal(self):
        self.sesion.get.side_effect = requests.Timeout()
        with self.assertRaises(ProveedorNoDisponible):
            OpenMeteoAdapter(self.sesion).condiciones()

    def test_rechaza_esquemas_y_numeros_invalidos(self):
        for payload in [[], {}, {'current': {}}, {**respuesta_valida(), 'current_units': {}},
                        {**respuesta_valida(), 'current': {'temperature_2m': True, 'precipitation': 0, 'time':'x'}},
                        {**respuesta_valida(), 'current': {'temperature_2m': float('nan'), 'precipitation':0, 'time':'x'}}]:
            with self.subTest(payload=payload):
                self.sesion.get.return_value.json.return_value = payload
                with self.assertRaises(ProveedorNoDisponible): OpenMeteoAdapter(self.sesion).condiciones()

    def test_no_acepta_errores_ni_redirecciones(self):
        for status in [301, 429, 500]:
            self.sesion.get.return_value.status_code=status
            with self.assertRaises(ProveedorNoDisponible): OpenMeteoAdapter(self.sesion).condiciones()

    def test_caso_de_uso_recibe_puerto_inyectado(self):
        proveedor = Mock()
        proveedor.condiciones.return_value = {'temperatura_c': 20}
        self.assertEqual(ConsultaClimaService(proveedor).consultar(), {'temperatura_c':20})

    @patch('apps.integraciones.views.OpenMeteoAdapter')
    def test_endpoint_cachea_solo_respuesta_valida(self, adapter):
        adapter.return_value.condiciones.return_value = {'temperatura_c':20}
        for _ in range(2): self.assertEqual(self.client.get('/api/v1/integraciones/clima/').status_code,200)
        self.assertEqual(adapter.return_value.condiciones.call_count,1)

    @patch('apps.integraciones.views.OpenMeteoAdapter')
    def test_falla_externa_responde_503_traducido(self, adapter):
        with override('en'):
            from django.utils.translation import gettext
            mensaje=gettext('El clima no está disponible. Puedes continuar tu reserva.')
        adapter.return_value.condiciones.side_effect=ProveedorNoDisponible(mensaje)
        respuesta=self.client.get('/api/v1/integraciones/clima/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(respuesta.status_code,503)
        self.assertIn('Weather',respuesta.json()['error']['mensaje'])

    def test_aliado_esta_pendiente_sin_inventar_datos(self):
        dato=self.client.get('/api/v1/integraciones/aliado/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(dato.status_code,503)
        self.assertEqual(dato.json()['error']['codigo'],'ALIADO-PENDIENTE')
        self.assertIn('partner team',dato.json()['error']['mensaje'])

    def test_landing_y_catalogo_javascript_usan_idioma(self):
        respuesta=self.client.get('/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertContains(respuesta,'More time for you.')
        self.assertContains(respuesta,'lang="en"')
        self.assertNotContains(respuesta,'Datos de prueba:')
        js=self.client.get('/jsi18n/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertContains(js,'My bookings')
        es=self.client.get('/', HTTP_ACCEPT_LANGUAGE='es')
        self.assertContains(es,'Más tiempo para ti.')

    def test_cambio_idioma_guarda_preferencia(self):
        respuesta=self.client.post('/i18n/setlang/', {'language':'en','next':'/'})
        self.assertEqual(respuesta.status_code,302)
        self.assertEqual(respuesta.cookies['django_language'].value,'en')
