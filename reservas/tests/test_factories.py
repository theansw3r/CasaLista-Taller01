"""La Factory debe cambiar de comportamiento SOLO con la variable de entorno."""

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from ..domain.tarifas import TarifaBase, TarifaDinamica
from ..infra.factories import CalculadorTarifaFactory, NotificadorFactory
from ..infra.notificaciones import NotificadorConsola, NotificadorEmail


class NotificadorFactoryTests(TestCase):
    @override_settings(NOTIFICADOR_TYPE="MOCK")
    def test_mock_devuelve_el_notificador_de_consola(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorConsola)

    @override_settings(NOTIFICADOR_TYPE="REAL")
    def test_real_devuelve_el_notificador_de_correo(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorEmail)

    @override_settings(NOTIFICADOR_TYPE="mock")
    def test_la_variable_no_distingue_mayusculas(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorConsola)

    @override_settings(NOTIFICADOR_TYPE="TELEPATIA")
    def test_un_valor_desconocido_falla_de_forma_explicita(self):
        with self.assertRaises(ImproperlyConfigured):
            NotificadorFactory.crear()

    @override_settings(NOTIFICADOR_TYPE="MOCK")
    def test_el_argumento_explicito_gana_sobre_el_entorno(self):
        self.assertIsInstance(NotificadorFactory.crear("REAL"), NotificadorEmail)


class CalculadorTarifaFactoryTests(TestCase):
    @override_settings(TARIFA_TYPE="BASE")
    def test_base_devuelve_la_tarifa_simple(self):
        self.assertIsInstance(CalculadorTarifaFactory.crear(), TarifaBase)

    @override_settings(TARIFA_TYPE="DINAMICA")
    def test_dinamica_devuelve_la_tarifa_con_recargos(self):
        self.assertIsInstance(CalculadorTarifaFactory.crear(), TarifaDinamica)

    def test_expone_las_opciones_disponibles(self):
        self.assertEqual(CalculadorTarifaFactory.opciones(), ["BASE", "DINAMICA"])
