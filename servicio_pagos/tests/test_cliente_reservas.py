import pytest
import requests

from pagos.errores import ErrorDeReservas, ReservasNoDisponible
from pagos.reservas import ClienteReservas


class RespuestaFalsa:
    def __init__(self, estado, cuerpo=None):
        self.status_code = estado
        self.ok = estado < 400
        self._cuerpo = cuerpo

    def json(self):
        if self._cuerpo is None:
            raise ValueError("no es JSON")
        return self._cuerpo


class SesionFalsa:
    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas = []

    def request(self, metodo, url, headers, timeout):
        self.llamadas.append((metodo, url, headers))
        if self.error:
            raise self.error
        return self.respuesta


def cliente_con(sesion):
    return ClienteReservas("http://django:8000/", "secreto", sesion=sesion)


def test_reenvia_el_jwt_del_cliente_a_django():
    sesion = SesionFalsa(RespuestaFalsa(200, {"id": 7, "estado": "PENDIENTE"}))

    cliente_con(sesion).obtener(7, "Bearer abc", "req-1")

    metodo, url, cabeceras = sesion.llamadas[0]
    assert (metodo, url) == ("GET", "http://django:8000/api/v1/reservas/7/")
    assert cabeceras["Authorization"] == "Bearer abc"
    assert cabeceras["X-Request-ID"] == "req-1"


def test_confirmar_usa_el_token_de_servicio_y_no_el_del_cliente():
    sesion = SesionFalsa(RespuestaFalsa(200, {"id": 7, "estado": "CONFIRMADA"}))

    cliente_con(sesion).confirmar(7)

    metodo, url, cabeceras = sesion.llamadas[0]
    assert (metodo, url) == ("POST", "http://django:8000/interno/reservas/7/confirmacion/")
    assert cabeceras["X-Token-Servicio"] == "secreto"
    assert "Authorization" not in cabeceras


def test_si_django_no_contesta_lanza_reservas_no_disponible():
    sesion = SesionFalsa(error=requests.ConnectionError("conexion rechazada"))

    with pytest.raises(ReservasNoDisponible):
        cliente_con(sesion).obtener(7, "Bearer abc")


def test_un_500_de_django_tambien_cuenta_como_no_disponible():
    sesion = SesionFalsa(RespuestaFalsa(500))

    with pytest.raises(ReservasNoDisponible):
        cliente_con(sesion).obtener(7, "Bearer abc")


def test_un_4xx_de_django_conserva_su_codigo():
    cuerpo = {"error": {"codigo": "RES-04", "mensaje": "No existe la reserva 7."}}
    sesion = SesionFalsa(RespuestaFalsa(404, cuerpo))

    with pytest.raises(ErrorDeReservas) as error:
        cliente_con(sesion).obtener(7, "Bearer abc")

    assert error.value.estado_http == 404
    assert error.value.codigo == "RES-04"
    assert str(error.value) == "No existe la reserva 7."
