"""Pruebas del modulo Catalogo: la busqueda tiene que respetar RN-07."""

from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalogo.dominio.excepciones import ProfesionalNoEncontrado, ServicioInactivo
from apps.catalogo.dominio.precios import CalculadoraDeServicio
from apps.catalogo.services import CatalogoService
from apps.comun.pruebas import crear_profesional, crear_servicio


class ServicioFalso:
    def __init__(self, precio="50000", minutos=60, activo=True):
        self.pk = 1
        self.nombre = "Servicio falso"
        self.precio_base = Decimal(precio)
        self.duracion_minutos = minutos
        self.activo = activo


class CalculadoraDeServicioTest(SimpleTestCase):
    def test_multiplica_precio_por_cantidad(self):
        self.assertEqual(
            CalculadoraDeServicio.precio(ServicioFalso(), 3), Decimal("150000.00")
        )

    def test_siempre_devuelve_dos_decimales(self):
        self.assertEqual(
            CalculadoraDeServicio.precio(ServicioFalso("33333.333"), 1),
            Decimal("33333.33"),
        )

    def test_multiplica_duracion_por_cantidad(self):
        self.assertEqual(CalculadoraDeServicio.duracion(ServicioFalso(), 2), 120)

    def test_un_servicio_inactivo_no_se_puede_vender(self):
        with self.assertRaises(ServicioInactivo):
            CalculadoraDeServicio.exigir_disponible(ServicioFalso(activo=False))


class CatalogoServiceTest(TestCase):
    def setUp(self):
        self.servicio = CatalogoService()
        self.laureles = crear_profesional(nombre="Cubre Laureles", zonas="Laureles")
        self.envigado = crear_profesional(nombre="Cubre Envigado", zonas="Envigado")
        self.sin_verificar = crear_profesional(
            nombre="Sin verificar", verificado=False, zonas="Laureles"
        )

    def test_rn07_solo_aparecen_los_verificados(self):
        nombres = [p.nombre for p in self.servicio.buscar_profesionales()]
        self.assertNotIn("Sin verificar", nombres)

    def test_rn07_filtra_por_zona(self):
        encontrados = self.servicio.buscar_profesionales(zona="Laureles")
        self.assertEqual([p.nombre for p in encontrados], ["Cubre Laureles"])

    def test_la_zona_no_distingue_mayusculas(self):
        encontrados = self.servicio.buscar_profesionales(zona="laureles")
        self.assertEqual(len(encontrados), 1)

    def test_una_zona_sin_cobertura_no_devuelve_nada(self):
        self.assertEqual(self.servicio.buscar_profesionales(zona="Sabaneta"), [])

    def test_busca_por_nombre(self):
        encontrados = self.servicio.buscar_profesionales(texto="Envigado")
        self.assertEqual([p.nombre for p in encontrados], ["Cubre Envigado"])

    def test_el_catalogo_omite_los_servicios_dados_de_baja(self):
        crear_servicio(self.laureles, nombre="Vigente")
        crear_servicio(self.laureles, nombre="Retirado", activo=False)

        servicios = self.servicio.servicios_de(self.laureles.pk)

        self.assertEqual(len(servicios), 1)
        self.assertTrue(servicios[0].nombre.startswith("Vigente"))

    def test_404_si_el_profesional_no_existe(self):
        with self.assertRaises(ProfesionalNoEncontrado):
            self.servicio.servicios_de(999999)

    def test_404_si_el_profesional_no_esta_verificado(self):
        """Un profesional sin verificar no tiene catalogo publico."""
        with self.assertRaises(ProfesionalNoEncontrado):
            self.servicio.servicios_de(self.sin_verificar.pk)


class CatalogoAPITest(APITestCase):
    def setUp(self):
        self.profesional = crear_profesional(zonas="Laureles,Belen")
        self.servicio = crear_servicio(self.profesional, precio="85000", minutos=60)

    def test_200_la_busqueda_es_publica(self):
        respuesta = self.client.get(
            reverse("catalogo:profesionales"), {"zona": "Laureles"}
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]["zonas"], ["Laureles", "Belen"])

    def test_200_el_catalogo_de_un_profesional(self):
        respuesta = self.client.get(
            reverse(
                "catalogo:servicios-del-profesional", args=[self.profesional.pk]
            )
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data[0]["precio_base"], "85000.00")

    def test_404_si_el_profesional_no_existe(self):
        respuesta = self.client.get(
            reverse("catalogo:servicios-del-profesional", args=[999999])
        )

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(respuesta.data["error"]["codigo"], "CAT-02")
