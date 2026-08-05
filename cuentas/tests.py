from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from reservas.models import Cliente


class RegistroClienteTests(TestCase):
    def setUp(self):
        self.url = reverse("cuentas:registro")

    def test_muestra_formulario_en_blanco(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Crear cuenta")

    def test_registra_el_usuario_crea_el_cliente_y_lo_autentica(self):
        respuesta = self.client.post(
            self.url,
            data={
                "username": "ana",
                "email": "ana@casalista.co",
                "nombre": "Ana Restrepo",
                "telefono": "3001234567",
                "password1": "clave-segura-123",
                "password2": "clave-segura-123",
            },
        )

        self.assertRedirects(respuesta, reverse("portal:inicio"))
        usuario = User.objects.get(username="ana")
        self.assertTrue(Cliente.objects.filter(usuario=usuario, nombre="Ana Restrepo").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_contrasenas_que_no_coinciden_no_crean_nada(self):
        respuesta = self.client.post(
            self.url,
            data={
                "username": "ana",
                "email": "ana@casalista.co",
                "nombre": "Ana Restrepo",
                "password1": "clave-segura-123",
                "password2": "otra-clave",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username="ana").exists())
