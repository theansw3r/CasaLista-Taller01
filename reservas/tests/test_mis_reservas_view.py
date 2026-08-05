"""MisReservasListView solo debe mostrar las reservas del cliente autenticado."""

from django.test import TestCase
from django.urls import reverse

from ..domain.reserva_builder import ReservaBuilder
from .factoria_de_datos import crear_bloque, crear_cliente, crear_profesional, crear_servicio


class MisReservasListViewTests(TestCase):
    def setUp(self):
        self.url = reverse("portal:mis-reservas")
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)

    def _crear_reserva(self, cliente):
        bloque = crear_bloque(self.profesional)
        return (
            ReservaBuilder()
            .para_cliente(cliente)
            .en_bloque(bloque)
            .en_direccion("Calle 30 #45-12", "Laureles")
            .agregar_servicio(self.servicio)
            .build()
        )

    def test_exige_autenticacion(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)

    def test_solo_lista_las_reservas_propias(self):
        reserva_propia = self._crear_reserva(self.cliente)
        otro_cliente = crear_cliente(nombre="Otro Cliente", email="otro@casalista.co")
        self._crear_reserva(otro_cliente)

        self.client.force_login(self.cliente.usuario)
        respuesta = self.client.get(self.url)

        self.assertEqual(list(respuesta.context["reservas"]), [reserva_propia])

    def test_usuario_sin_perfil_de_cliente_es_redirigido_con_aviso(self):
        """Antes veia una lista vacia, que sugeria que podia tener reservas."""
        self.client.force_login(self.profesional.usuario)

        respuesta = self.client.get(self.url, follow=True)

        self.assertRedirects(respuesta, reverse("portal:inicio"))
        self.assertContains(respuesta, "no tiene perfil de cliente")
