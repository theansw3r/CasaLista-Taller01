"""Pruebas del modulo Cuentas: politica de cobertura (RN-07) y registro."""

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comun.pruebas import crear_cliente, crear_profesional
from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.dominio.excepciones import (
    CorreoYaRegistrado,
    ProfesionalNoHabilitado,
)
from apps.cuentas.dto import RegistrarClienteCommand
from apps.cuentas.models import Cliente
from apps.cuentas.services import RegistroClienteService


class ProfesionalFalso:
    """Doble sin base de datos.

    Que la politica se pueda probar contra este objeto de tres lineas es la
    demostracion practica de que la regla NO depende del ORM. Si `cubreZona()`
    estuviera dentro del modelo, esta prueba necesitaria base de datos.
    """

    def __init__(self, zonas: str, verificado: bool = True):
        self.pk = 1
        self.nombre = "Profesional falso"
        self.zonas_cobertura = zonas
        self.verificado = verificado


class PoliticaDeCoberturaTest(SimpleTestCase):
    def test_parte_las_zonas_y_les_quita_espacios(self):
        profesional = ProfesionalFalso(" Laureles , Belen ,, Envigado ")
        self.assertEqual(
            PoliticaDeCobertura.zonas_de(profesional),
            ["Laureles", "Belen", "Envigado"],
        )

    def test_la_comparacion_ignora_mayusculas(self):
        profesional = ProfesionalFalso("Laureles,Belen")
        self.assertTrue(PoliticaDeCobertura.cubre_zona(profesional, "laureles"))
        self.assertTrue(PoliticaDeCobertura.cubre_zona(profesional, "  LAURELES  "))

    def test_una_zona_no_cubierta_da_falso(self):
        profesional = ProfesionalFalso("Laureles")
        self.assertFalse(PoliticaDeCobertura.cubre_zona(profesional, "Sabaneta"))

    def test_una_zona_vacia_nunca_esta_cubierta(self):
        profesional = ProfesionalFalso("Laureles")
        self.assertFalse(PoliticaDeCobertura.cubre_zona(profesional, ""))

    def test_rn07_exige_verificacion_y_cobertura(self):
        sin_verificar = ProfesionalFalso("Laureles", verificado=False)
        with self.assertRaises(ProfesionalNoHabilitado):
            PoliticaDeCobertura.exigir_habilitado(sin_verificar, "Laureles")

        fuera_de_zona = ProfesionalFalso("Laureles")
        with self.assertRaises(ProfesionalNoHabilitado):
            PoliticaDeCobertura.exigir_habilitado(fuera_de_zona, "Sabaneta")

    def test_el_error_dice_que_zonas_si_cubre(self):
        profesional = ProfesionalFalso("Laureles,Belen")
        with self.assertRaises(ProfesionalNoHabilitado) as capturado:
            PoliticaDeCobertura.exigir_habilitado(profesional, "Sabaneta")

        self.assertEqual(
            capturado.exception.contexto["zonas_cubiertas"], ["Laureles", "Belen"]
        )


class RegistroClienteServiceTest(TestCase):
    def test_crea_la_cuenta_y_el_perfil(self):
        cliente = RegistroClienteService().registrar(
            RegistrarClienteCommand(
                correo="Nueva@Correo.com",
                contrasena="contrasena-larga",
                nombre="Nueva Clienta",
            )
        )

        self.assertEqual(cliente.usuario.username, "nueva@correo.com")
        self.assertTrue(cliente.usuario.check_password("contrasena-larga"))

    def test_no_permite_dos_cuentas_con_el_mismo_correo(self):
        comando = RegistrarClienteCommand(
            correo="repetido@correo.com",
            contrasena="contrasena-larga",
            nombre="Primera",
        )
        RegistroClienteService().registrar(comando)

        with self.assertRaises(CorreoYaRegistrado):
            RegistroClienteService().registrar(comando)

        self.assertEqual(Cliente.objects.filter(nombre="Primera").count(), 1)


class CuentasAPITest(APITestCase):
    def test_201_registro_de_cliente(self):
        respuesta = self.client.post(
            reverse("cuentas:registro-cliente"),
            {
                "correo": "api@correo.com",
                "contrasena": "contrasena-larga",
                "nombre": "Cliente API",
                "telefono": "3001234567",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["correo"], "api@correo.com")
        self.assertNotIn("contrasena", respuesta.data)

    def test_400_si_la_contrasena_es_corta(self):
        respuesta = self.client.post(
            reverse("cuentas:registro-cliente"),
            {"correo": "corta@correo.com", "contrasena": "123", "nombre": "X"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_400_si_el_correo_ya_existe(self):
        cuerpo = {
            "correo": "duplicado@correo.com",
            "contrasena": "contrasena-larga",
            "nombre": "Duplicado",
        }
        self.client.post(reverse("cuentas:registro-cliente"), cuerpo, format="json")

        respuesta = self.client.post(
            reverse("cuentas:registro-cliente"), cuerpo, format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["error"]["codigo"], "CTA-01")

    def test_201_el_profesional_nace_sin_verificar(self):
        respuesta = self.client.post(
            reverse("cuentas:registro-profesional"),
            {
                "correo": "pro@correo.com",
                "contrasena": "contrasena-larga",
                "nombre": "Pro API",
                "documento": "999888",
                "zonas_cobertura": ["Laureles", "Belen"],
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertFalse(respuesta.data["verificado"])
        self.assertEqual(respuesta.data["zonas"], ["Laureles", "Belen"])

    def test_el_token_jwt_da_acceso_a_los_endpoints_privados(self):
        """Prueba del camino de autenticacion completo, sin sesion."""
        cliente = crear_cliente()
        cliente.usuario.set_password("contrasena-larga")
        cliente.usuario.save()

        token = self.client.post(
            reverse("cuentas:token"),
            {"username": cliente.usuario.username, "password": "contrasena-larga"},
            format="json",
        ).data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        respuesta = self.client.get(reverse("cuentas:perfil"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["cliente"]["nombre"], cliente.nombre)
        self.assertIsNone(respuesta.data["profesional"])

    def test_401_al_perfil_sin_token(self):
        respuesta = self.client.get(reverse("cuentas:perfil"))
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_perfil_distingue_los_dos_roles(self):
        profesional = crear_profesional()
        self.client.force_authenticate(user=profesional.usuario)

        respuesta = self.client.get(reverse("cuentas:perfil"))

        self.assertIsNone(respuesta.data["cliente"])
        self.assertEqual(respuesta.data["profesional"]["nombre"], profesional.nombre)
