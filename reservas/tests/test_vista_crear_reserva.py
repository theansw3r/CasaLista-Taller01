"""La vista solo traduce HTTP: entrada valida -> 201, regla violada -> su codigo."""

import json

from django.test import RequestFactory, TestCase
from django.urls import reverse

from ..domain.excepciones import ServicioInactivo
from ..models import Reserva
from ..views import CrearReservaView
from .factoria_de_datos import (
    crear_bloque,
    crear_cliente,
    crear_profesional,
    crear_servicio,
)


class ServicioDeMentira:
    """Doble que cumple el contrato del Service sin tocar la base de datos."""

    def crear_reserva(self, comando):
        raise ServicioInactivo("el doble siempre rechaza")


class CrearReservaViewTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.profesional = crear_profesional()
        self.servicio = crear_servicio(self.profesional)
        self.bloque = crear_bloque(self.profesional)
        self.url = reverse("reservas:crear-reserva")

    def _autenticar(self):
        self.client.force_login(self.cliente.usuario)

    def _payload(self, **cambios):
        datos = {
            "bloque_id": self.bloque.pk,
            "direccion": "Calle 30 #45-12",
            "zona": "Laureles",
            "servicios": [{"servicio_id": self.servicio.pk, "cantidad": 1}],
        }
        datos.update(cambios)
        return datos

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_crea_la_reserva_y_responde_201(self):
        self._autenticar()

        respuesta = self._post(self._payload())

        self.assertEqual(respuesta.status_code, 201)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["estado"], Reserva.Estado.PENDIENTE)
        self.assertEqual(cuerpo["total"], "80000.00")
        self.assertEqual(len(cuerpo["detalles"]), 1)

    def test_acepta_tambien_formulario_codificado(self):
        self._autenticar()

        respuesta = self.client.post(
            self.url,
            data={
                "bloque_id": self.bloque.pk,
                "direccion": "Calle 30 #45-12",
                "zona": "Laureles",
                "servicios": json.dumps(
                    [{"servicio_id": self.servicio.pk, "cantidad": 1}]
                ),
            },
        )

        self.assertEqual(respuesta.status_code, 201)

    def test_exige_autenticacion(self):
        respuesta = self._post(self._payload())

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_datos_mal_formados_responden_400(self):
        self._autenticar()

        respuesta = self._post(self._payload(servicios=[]))

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("servicios", respuesta.json()["errores"])

    def test_una_regla_de_negocio_devuelve_su_codigo(self):
        self._autenticar()

        respuesta = self._post(self._payload(zona="Sabaneta"))

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["codigo"], "RN-07")

    def test_un_bloque_ya_reservado_devuelve_rn01(self):
        self._autenticar()
        self._post(self._payload())

        respuesta = self._post(self._payload())

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["codigo"], "RN-01")

    def test_un_recurso_inexistente_devuelve_404(self):
        self._autenticar()

        respuesta = self._post(self._payload(bloque_id=99999))

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["codigo"], "VAL-05")

    def test_la_vista_acepta_cualquier_service_inyectado(self):
        """Evidencia de la inyeccion: la vista solo conoce crear_reserva()."""
        peticion = RequestFactory().post(
            self.url,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        peticion.user = self.cliente.usuario

        respuesta = CrearReservaView.as_view(servicio=ServicioDeMentira)(peticion)

        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(json.loads(respuesta.content)["codigo"], "VAL-04")
        self.assertEqual(Reserva.objects.count(), 0)
