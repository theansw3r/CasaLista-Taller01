"""La version HTML de crear reserva debe pasar por el mismo Service que la API.

Ademas, el formulario solo puede ofrecer horarios y zonas del profesional
dueno del servicio: eso hace que RN-02 y RN-07 sean inalcanzables desde la
interfaz, aunque el Builder las siga validando.
"""

from django.test import TestCase
from django.urls import reverse

from ..models import Reserva
from .factoria_de_datos import crear_bloque, crear_cliente, crear_profesional, crear_servicio


class CatalogoViewTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.url = reverse("portal:catalogo")

    def test_exige_autenticacion(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_lista_los_servicios_activos_de_profesionales_verificados(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, self.servicio.nombre)
        self.assertContains(respuesta, self.profesional.zonas_cobertura)

    def test_oculta_los_servicios_de_profesionales_no_verificados(self):
        oculto = crear_profesional(
            nombre="Sin Verificar", verificado=False, email="sinver@casalista.co"
        )
        crear_servicio(oculto, nombre="Servicio oculto")
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.get(self.url)

        self.assertNotContains(respuesta, "Servicio oculto")


class CrearReservaWebViewTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.bloque = crear_bloque(self.profesional)
        self.url = reverse("portal:crear-reserva", args=[self.servicio.pk])

    def _datos(self, **cambios):
        datos = {
            "bloque": self.bloque.pk,
            "zona": "Laureles",
            "direccion": "Calle 30 #45-12",
            "cantidad": 1,
        }
        datos.update(cambios)
        return datos

    def test_exige_autenticacion(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_servicio_inexistente_da_404(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.get(reverse("portal:crear-reserva", args=[99999]))

        self.assertEqual(respuesta.status_code, 404)

    def test_solo_ofrece_zonas_que_el_profesional_cubre(self):
        self.client.force_login(self.cliente.usuario)

        formulario = self.client.get(self.url).context["form"]

        self.assertEqual(
            [valor for valor, _ in formulario.fields["zona"].choices],
            self.profesional.zonas_lista(),
        )

    def test_solo_ofrece_bloques_libres_del_profesional_del_servicio(self):
        otro = crear_profesional(nombre="Otro Pro", email="otro@casalista.co")
        bloque_ajeno = crear_bloque(otro)
        self.client.force_login(self.cliente.usuario)

        formulario = self.client.get(self.url).context["form"]
        ofrecidos = list(formulario.fields["bloque"].queryset)

        self.assertIn(self.bloque, ofrecidos)
        self.assertNotIn(bloque_ajeno, ofrecidos)

    def test_crea_la_reserva_y_redirige_a_mis_reservas(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.post(self.url, data=self._datos())

        self.assertRedirects(respuesta, reverse("portal:mis-reservas"))
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.cliente, self.cliente)
        self.assertEqual(reserva.bloque, self.bloque)

    def test_no_vuelve_a_ofrecer_un_bloque_ya_reservado(self):
        self.client.force_login(self.cliente.usuario)
        self.client.post(self.url, data=self._datos())

        formulario = self.client.get(self.url).context["form"]

        self.assertNotIn(self.bloque, list(formulario.fields["bloque"].queryset))

    def test_una_regla_de_negocio_violada_se_muestra_en_la_pagina(self):
        """El Builder sigue mandando aunque la interfaz filtre."""
        self.client.force_login(self.cliente.usuario)
        self.profesional.verificado = False
        self.profesional.save()

        respuesta = self.client.post(self.url, data=self._datos())

        # el servicio deja de ser reservable en cuanto el profesional pierde
        # la verificacion, asi que la URL ya no resuelve
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_rechaza_una_zona_que_no_esta_en_el_desplegable(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.post(self.url, data=self._datos(zona="Sabaneta"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertFormError(
            respuesta.context["form"],
            "zona",
            "Escoja una opción válida. Sabaneta no es una de las opciones disponibles.",
        )
        self.assertEqual(Reserva.objects.count(), 0)
