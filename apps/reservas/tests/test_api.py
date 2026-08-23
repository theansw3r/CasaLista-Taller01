"""
Pruebas de la capa de presentacion.

Aqui no se vuelven a probar las reglas: se comprueba la TRADUCCION. Que una
regla violada en el dominio salga por HTTP con el codigo correcto y con el
cuerpo de error acordado.

Es la prueba de que el manejador central de excepciones funciona: las vistas
no tienen un solo try/except y aun asi cada error sale con su codigo.
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comun.pruebas import (
    crear_bloque,
    crear_cliente,
    crear_profesional,
    crear_servicio,
    escenario_basico,
)
from apps.reservas.models import BloqueDisponibilidad, Reserva


class CrearReservaAPITest(APITestCase):
    """POST /api/v1/reservas/ con sus cuatro codigos de respuesta."""

    def setUp(self):
        self.escenario = escenario_basico()
        self.url = reverse("reservas:reservas")
        self.client.force_authenticate(user=self.escenario["cliente"].usuario)

    def _cuerpo(self, **cambios) -> dict:
        cuerpo = {
            "bloque_id": self.escenario["bloque"].pk,
            "direccion": "Calle 33 #70-21",
            "zona": "Laureles",
            "servicios": [{"servicio_id": self.escenario["servicio"].pk, "cantidad": 1}],
        }
        cuerpo.update(cambios)
        return cuerpo

    # --- 201 -----------------------------------------------------------
    def test_201_crea_la_reserva(self):
        respuesta = self.client.post(self.url, self._cuerpo(), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado"], Reserva.Estado.PENDIENTE)
        self.assertEqual(respuesta.data["total"], "50000.00")
        self.assertEqual(len(respuesta.data["detalles"]), 1)

    def test_201_devuelve_el_identificador_de_correlacion(self):
        respuesta = self.client.post(self.url, self._cuerpo(), format="json")
        self.assertIn("X-Request-ID", respuesta.headers)

    # --- 400 -----------------------------------------------------------
    def test_400_si_falta_un_campo(self):
        cuerpo = self._cuerpo()
        del cuerpo["direccion"]

        respuesta = self.client.post(self.url, cuerpo, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("direccion", respuesta.data["error"]["contexto"]["campos"])

    def test_400_si_la_lista_de_servicios_viene_vacia(self):
        respuesta = self.client.post(
            self.url, self._cuerpo(servicios=[]), format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_400_si_la_cantidad_no_es_positiva(self):
        respuesta = self.client.post(
            self.url,
            self._cuerpo(
                servicios=[{"servicio_id": self.escenario["servicio"].pk, "cantidad": 0}]
            ),
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    # --- 404 -----------------------------------------------------------
    def test_404_si_la_franja_no_existe(self):
        respuesta = self.client.post(
            self.url, self._cuerpo(bloque_id=999999), format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(respuesta.data["error"]["codigo"], "AGD-02")

    def test_404_si_el_servicio_no_existe(self):
        respuesta = self.client.post(
            self.url,
            self._cuerpo(servicios=[{"servicio_id": 999999, "cantidad": 1}]),
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    # --- 409 -----------------------------------------------------------
    def test_409_rn01_si_la_franja_ya_esta_tomada(self):
        self.client.post(self.url, self._cuerpo(), format="json")

        self.client.force_authenticate(user=crear_cliente(nombre="Segundo").usuario)
        respuesta = self.client.post(self.url, self._cuerpo(), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "RN-01")

    def test_409_rn02_si_los_servicios_son_de_dos_profesionales(self):
        otro = crear_profesional(nombre="Otro")
        respuesta = self.client.post(
            self.url,
            self._cuerpo(
                servicios=[
                    {"servicio_id": self.escenario["servicio"].pk, "cantidad": 1},
                    {"servicio_id": crear_servicio(otro).pk, "cantidad": 1},
                ]
            ),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "RN-02")

    def test_409_rn07_si_el_profesional_no_cubre_la_zona(self):
        respuesta = self.client.post(
            self.url, self._cuerpo(zona="Sabaneta"), format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "RN-07")
        self.assertIn("zonas_cubiertas", respuesta.data["error"]["contexto"])

    def test_409_si_los_servicios_no_caben_en_la_franja(self):
        largo = crear_servicio(self.escenario["profesional"], minutos=300)
        respuesta = self.client.post(
            self.url,
            self._cuerpo(servicios=[{"servicio_id": largo.pk, "cantidad": 1}]),
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    # --- 401 -----------------------------------------------------------
    def test_401_sin_autenticar(self):
        self.client.force_authenticate(user=None)
        respuesta = self.client.post(self.url, self._cuerpo(), format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Forma del error -----------------------------------------------
    def test_todos_los_errores_tienen_la_misma_forma(self):
        """Da igual si el error lo genero DRF o el dominio."""
        de_drf = self.client.post(self.url, {}, format="json")
        del_dominio = self.client.post(
            self.url, self._cuerpo(bloque_id=999999), format="json"
        )

        for respuesta in (de_drf, del_dominio):
            self.assertIn("error", respuesta.data)
            self.assertIn("codigo", respuesta.data["error"])
            self.assertIn("mensaje", respuesta.data["error"])


class ConsultarReservasAPITest(APITestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.client.force_authenticate(user=self.escenario["cliente"].usuario)
        self.reserva_id = self.client.post(
            reverse("reservas:reservas"),
            {
                "bloque_id": self.escenario["bloque"].pk,
                "direccion": "Calle 33 #70-21",
                "zona": "Laureles",
                "servicios": [
                    {"servicio_id": self.escenario["servicio"].pk, "cantidad": 1}
                ],
            },
            format="json",
        ).data["id"]

    def test_200_lista_las_reservas_del_cliente(self):
        respuesta = self.client.get(reverse("reservas:reservas"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

    def test_200_detalle_de_una_reserva_propia(self):
        respuesta = self.client.get(
            reverse("reservas:detalle", args=[self.reserva_id])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_404_si_la_reserva_no_existe(self):
        respuesta = self.client.get(reverse("reservas:detalle", args=[999999]))
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_403_si_la_reserva_es_de_otro_cliente(self):
        self.client.force_authenticate(user=crear_cliente(nombre="Intruso").usuario)
        respuesta = self.client.get(
            reverse("reservas:detalle", args=[self.reserva_id])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_200_cancela_y_libera_la_franja(self):
        respuesta = self.client.post(
            reverse("reservas:cancelacion", args=[self.reserva_id]),
            {"motivo": "Ya no necesito el servicio"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], Reserva.Estado.CANCELADA)

    def test_409_al_cancelar_dos_veces(self):
        url = reverse("reservas:cancelacion", args=[self.reserva_id])
        self.client.post(url, {}, format="json")

        respuesta = self.client.post(url, {}, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "RES-05")


class DisponibilidadAPITest(APITestCase):
    def setUp(self):
        self.profesional = crear_profesional()
        self.url = reverse("reservas:disponibilidad")

    def _cuerpo(self, en_horas: int = 24, duracion: int = 2) -> dict:
        inicio = timezone.now() + timedelta(hours=en_horas)
        return {
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(hours=duracion)).isoformat(),
        }

    def test_201_el_profesional_publica_una_franja(self):
        self.client.force_authenticate(user=self.profesional.usuario)

        respuesta = self.client.post(self.url, self._cuerpo(), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado"], BloqueDisponibilidad.Estado.LIBRE)
        self.assertEqual(respuesta.data["duracion_minutos"], 120)

    def test_409_si_la_franja_se_solapa(self):
        self.client.force_authenticate(user=self.profesional.usuario)
        self.client.post(self.url, self._cuerpo(24, 3), format="json")

        respuesta = self.client.post(self.url, self._cuerpo(25, 1), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["error"]["codigo"], "AGD-03")

    def test_404_si_la_cuenta_no_tiene_perfil_de_profesional(self):
        self.client.force_authenticate(user=crear_cliente().usuario)
        respuesta = self.client.post(self.url, self._cuerpo(), format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_si_el_rango_esta_al_reves(self):
        self.client.force_authenticate(user=self.profesional.usuario)
        inicio = timezone.now() + timedelta(hours=24)

        respuesta = self.client.post(
            self.url,
            {
                "inicio": inicio.isoformat(),
                "fin": (inicio - timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["error"]["codigo"], "AGD-01")

    def test_200_la_consulta_de_agenda_es_publica(self):
        crear_bloque(self.profesional)

        respuesta = self.client.get(
            self.url, {"profesional_id": self.profesional.pk}
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

    def test_400_si_falta_el_profesional_en_la_consulta(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
