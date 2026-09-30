import logging

import requests

from pagos.errores import ErrorDeReservas, ReservasNoDisponible

logger = logging.getLogger(__name__)


class ClienteReservas:
    """Unica parte del servicio que sabe que las reservas viven en Django."""

    def __init__(
        self, url_base: str, token_servicio: str, timeout: float = 5.0, sesion=None
    ) -> None:
        self.url_base = url_base.rstrip("/")
        self.token_servicio = token_servicio
        self.timeout = timeout
        self.sesion = sesion or requests.Session()

    def obtener(self, reserva_id: int, autorizacion: str, id_peticion: str = "") -> dict:
        # Se reenvia el JWT del cliente tal cual. Django ya sabe decidir si la
        # reserva es suya (403) o si no existe (404); no hay que repetirlo aca.
        return self._pedir(
            "GET",
            f"/api/v1/reservas/{reserva_id}/",
            {"Authorization": autorizacion},
            id_peticion,
        )

    def confirmar(self, reserva_id: int, id_peticion: str = "") -> dict:
        return self._pedir(
            "POST",
            f"/interno/reservas/{reserva_id}/confirmacion/",
            {"X-Token-Servicio": self.token_servicio},
            id_peticion,
        )

    def _pedir(self, metodo: str, ruta: str, cabeceras: dict, id_peticion: str) -> dict:
        if id_peticion:
            cabeceras["X-Request-ID"] = id_peticion
        try:
            respuesta = self.sesion.request(
                metodo, self.url_base + ruta, headers=cabeceras, timeout=self.timeout
            )
        except requests.RequestException as error:
            logger.error("Django no respondio a %s %s: %s", metodo, ruta, error)
            raise ReservasNoDisponible() from error

        if respuesta.status_code >= 500:
            logger.error("Django respondio %s a %s %s", respuesta.status_code, metodo, ruta)
            raise ReservasNoDisponible()

        cuerpo = self._leer_json(respuesta)
        if not respuesta.ok:
            raise ErrorDeReservas(respuesta.status_code, cuerpo)
        if not isinstance(cuerpo, dict):
            raise ReservasNoDisponible()
        return cuerpo

    @staticmethod
    def _leer_json(respuesta):
        try:
            return respuesta.json()
        except ValueError:
            return None
