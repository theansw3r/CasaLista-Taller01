from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.pagos.infraestructura.factories import PasarelaPagoFactory
from apps.pagos.infraestructura.pasarelas import (
    PasarelaPSE,
    PasarelaSimulada,
    PasarelaTarjeta,
)
from apps.reservas.dominio.puertos import CalculadorTarifa, Notificador
from apps.reservas.dominio.tarifas import TarifaBase, TarifaDinamica
from apps.reservas.infraestructura.factories import (
    CalculadorTarifaFactory,
    NotificadorFactory,
)
from apps.reservas.infraestructura.notificaciones import (
    NotificadorConsola,
    NotificadorEmail,
)


class NotificadorFactoryTest(SimpleTestCase):
    @override_settings(NOTIFICADOR_TYPE="MOCK")
    def test_mock_devuelve_el_de_consola(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorConsola)

    @override_settings(NOTIFICADOR_TYPE="REAL")
    def test_real_devuelve_el_de_correo(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorEmail)

    @override_settings(NOTIFICADOR_TYPE="mock")
    def test_no_distingue_mayusculas(self):
        self.assertIsInstance(NotificadorFactory.crear(), NotificadorConsola)

    def test_se_puede_forzar_una_variante_concreta(self):
        self.assertIsInstance(NotificadorFactory.crear("REAL"), NotificadorEmail)

    @override_settings(NOTIFICADOR_TYPE="TELEGRAMA")
    def test_un_valor_desconocido_falla_con_las_opciones_validas(self):
        with self.assertRaises(ImproperlyConfigured) as capturado:
            NotificadorFactory.crear()

        mensaje = str(capturado.exception)
        self.assertIn("NOTIFICADOR_TYPE", mensaje)
        self.assertIn("MOCK", mensaje)
        self.assertIn("REAL", mensaje)

    def test_todo_lo_que_devuelve_cumple_el_puerto(self):
        for tipo in NotificadorFactory.opciones():
            self.assertIsInstance(NotificadorFactory.crear(tipo), Notificador)


class CalculadorTarifaFactoryTest(SimpleTestCase):
    @override_settings(TARIFA_TYPE="BASE")
    def test_base(self):
        self.assertIsInstance(CalculadorTarifaFactory.crear(), TarifaBase)

    @override_settings(TARIFA_TYPE="DINAMICA")
    def test_dinamica(self):
        self.assertIsInstance(CalculadorTarifaFactory.crear(), TarifaDinamica)

    def test_todo_lo_que_devuelve_cumple_el_puerto(self):
        for tipo in CalculadorTarifaFactory.opciones():
            self.assertIsInstance(CalculadorTarifaFactory.crear(tipo), CalculadorTarifa)


class PasarelaPagoFactoryTest(SimpleTestCase):
    @override_settings(PASARELA_PAGO_TYPE="SIMULADA")
    def test_en_desarrollo_todo_medio_cae_en_la_simulada(self):
        self.assertIsInstance(PasarelaPagoFactory.para_medio("TARJETA"), PasarelaSimulada)
        self.assertIsInstance(PasarelaPagoFactory.para_medio("PSE"), PasarelaSimulada)

    @override_settings(PASARELA_PAGO_TYPE="TARJETA")
    def test_fuera_de_desarrollo_se_respeta_el_medio_del_cliente(self):
        self.assertIsInstance(PasarelaPagoFactory.para_medio("PSE"), PasarelaPSE)
        self.assertIsInstance(PasarelaPagoFactory.para_medio("TARJETA"), PasarelaTarjeta)

    def test_las_tres_opciones_estan_registradas(self):
        self.assertEqual(
            PasarelaPagoFactory.opciones(), ["PSE", "SIMULADA", "TARJETA"]
        )
