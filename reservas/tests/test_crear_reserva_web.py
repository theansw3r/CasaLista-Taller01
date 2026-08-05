"""La version HTML de crear reserva debe pasar por el mismo Service que la API."""

from django.test import TestCase
from django.urls import reverse

from ..models import Reserva
from .factoria_de_datos import crear_bloque, crear_cliente, crear_profesional, crear_servicio


class CrearReservaWebViewTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.bloque = crear_bloque(self.profesional)
        self.url = reverse("portal:crear-reserva")

    def test_exige_autenticacion(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)

    def test_muestra_el_formulario(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, str(self.servicio))
        # se relee de la base (como hace el ModelChoiceField) para verificar
        # que la hora mostrada ya esta convertida a la zona local.
        self.bloque.refresh_from_db()
        self.assertContains(respuesta, str(self.bloque))

    def test_crea_la_reserva_y_redirige_a_mis_reservas(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.post(
            self.url,
            data={
                "servicio": self.servicio.pk,
                "bloque": self.bloque.pk,
                "direccion": "Calle 30 #45-12",
                "zona": "Laureles",
            },
        )

        self.assertRedirects(respuesta, reverse("portal:mis-reservas"))
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(Reserva.objects.get().cliente, self.cliente)

    def test_una_regla_de_negocio_violada_se_muestra_en_la_pagina(self):
        self.client.force_login(self.cliente.usuario)

        respuesta = self.client.post(
            self.url,
            data={
                "servicio": self.servicio.pk,
                "bloque": self.bloque.pk,
                "direccion": "Calle 1",
                "zona": "Sabaneta",  # el profesional no cubre esta zona
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no cubre la zona")
        self.assertEqual(Reserva.objects.count(), 0)
