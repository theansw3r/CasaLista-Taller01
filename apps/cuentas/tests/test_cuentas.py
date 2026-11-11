from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalogo.services import CatalogoService
from apps.comun.pruebas import crear_cliente, crear_profesional
from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.dominio.excepciones import (
    CorreoYaRegistrado,
    ProfesionalNoHabilitado,
)
from apps.cuentas.dto import RegistrarClienteCommand
from apps.cuentas.models import Cliente, Profesional
from apps.cuentas.services import (
    RegistroClienteService,
    VerificacionProfesionalService,
)


class ProfesionalFalso:

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


class VerificacionProfesionalServiceTest(TestCase):
    """RN-07: verificar es lo que habilita a un profesional para recibir reservas."""

    def setUp(self):
        self.servicio = VerificacionProfesionalService()
        self.profesional = crear_profesional(verificado=False)

    def _consulta(self):
        return Profesional.objects.filter(pk=self.profesional.pk)

    def test_verificar_habilita_al_profesional(self):
        cambiados = self.servicio.verificar(self._consulta())

        self.profesional.refresh_from_db()
        self.assertEqual(cambiados, 1)
        self.assertTrue(self.profesional.verificado)

    def test_revocar_lo_saca_de_las_busquedas(self):
        self.servicio.verificar(self._consulta())

        self.servicio.revocar(self._consulta())

        self.profesional.refresh_from_db()
        self.assertFalse(self.profesional.verificado)

    def test_un_profesional_sin_verificar_no_aparece_en_el_catalogo(self):
        self.assertEqual(CatalogoService().buscar_profesionales(), [])

        self.servicio.verificar(self._consulta())

        encontrados = CatalogoService().buscar_profesionales()
        self.assertEqual([p.pk for p in encontrados], [self.profesional.pk])


class RegistroProfesionalDuplicadoTest(APITestCase):
    """Un documento repetido tiene que dar 400, nunca un 500."""

    def _cuerpo(self, **cambios):
        cuerpo = {
            "correo": "primero@correo.com",
            "contrasena": "contrasena-larga",
            "nombre": "Reparaciones",
            "documento": "1034989718",
            "descripcion": "Reparo electrodomesticos",
            "zonas_cobertura": ["Laureles"],
        }
        cuerpo.update(cambios)
        return cuerpo

    def test_400_si_el_documento_ya_existe(self):
        url = reverse("cuentas:registro-profesional")
        self.client.post(url, self._cuerpo(), format="json")

        respuesta = self.client.post(
            url, self._cuerpo(correo="segundo@correo.com"), format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["error"]["codigo"], "CTA-04")

    def test_no_deja_el_usuario_huerfano_si_falla(self):
        """Si el documento choca, tampoco debe quedar la cuenta creada."""
        url = reverse("cuentas:registro-profesional")
        self.client.post(url, self._cuerpo(), format="json")

        self.client.post(url, self._cuerpo(correo="segundo@correo.com"), format="json")

        from django.contrib.auth import get_user_model

        self.assertFalse(
            get_user_model().objects.filter(username="segundo@correo.com").exists()
        )

    def test_dos_profesionales_con_documentos_distintos_si_pueden(self):
        url = reverse("cuentas:registro-profesional")
        self.client.post(url, self._cuerpo(), format="json")

        respuesta = self.client.post(
            url,
            self._cuerpo(correo="otro@correo.com", documento="999888777"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
