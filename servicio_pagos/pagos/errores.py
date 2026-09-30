import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ErrorDePagos(Exception):
    """Misma idea que ErrorDeDominio en Django: cada error trae su codigo y su
    estado HTTP, y un solo manejador lo convierte en JSON."""

    codigo = "ERR-000"
    estado_http = 409
    mensaje_por_defecto = "La operacion viola una regla de negocio."

    def __init__(self, mensaje: str = "", **contexto) -> None:
        super().__init__(mensaje or self.mensaje_por_defecto)
        self.contexto = contexto

    def como_diccionario(self) -> dict:
        cuerpo = {"codigo": self.codigo, "mensaje": str(self)}
        if self.contexto:
            cuerpo["contexto"] = self.contexto
        return cuerpo


class DatosInvalidos(ErrorDePagos):
    codigo = "VAL-000"
    estado_http = 400
    mensaje_por_defecto = "La peticion tiene campos invalidos."


class SinCredenciales(ErrorDePagos):
    codigo = "HTTP-401"
    estado_http = 401
    mensaje_por_defecto = "Las credenciales de autenticacion no se proveyeron."


class PagoNoEncontrado(ErrorDePagos):
    codigo = "PAG-01"
    estado_http = 404
    mensaje_por_defecto = "El pago solicitado no existe."


class ReservaYaPagada(ErrorDePagos):
    codigo = "PAG-02"
    mensaje_por_defecto = "Esta reserva ya tiene un pago registrado."


class ReservaNoCobrable(ErrorDePagos):
    codigo = "PAG-03"
    mensaje_por_defecto = "La reserva no esta en un estado que admita pago."


class PagoRechazado(ErrorDePagos):
    codigo = "PAG-04"
    mensaje_por_defecto = "La pasarela rechazo el pago."


class PasarelaNoDisponible(ErrorDePagos):
    codigo = "PAG-05"
    estado_http = 502
    mensaje_por_defecto = "La pasarela de pagos no esta respondiendo."


class ReservasNoDisponible(ErrorDePagos):
    codigo = "PAG-06"
    estado_http = 503
    mensaje_por_defecto = (
        "No se pudo consultar la reserva. Intente de nuevo en un momento."
    )


class ReservaSinConfirmar(ErrorDePagos):
    codigo = "PAG-07"
    estado_http = 502
    mensaje_por_defecto = (
        "El cobro se aprobo pero la reserva no se pudo confirmar. "
        "El pago quedo registrado para conciliarlo."
    )


class ErrorDeReservas(ErrorDePagos):
    """Un 4xx que respondio Django. Se le devuelve al cliente tal cual, con el
    mismo codigo y mensaje, para no inventar otra version del error."""

    def __init__(self, estado_http: int, cuerpo) -> None:
        error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
        error = error if isinstance(error, dict) else {}
        super().__init__(error.get("mensaje", ""), **(error.get("contexto") or {}))
        self.estado_http = estado_http
        self.codigo = error.get("codigo", f"HTTP-{estado_http}")


MENSAJES_HTTP = {
    404: "La ruta no existe en el servicio de pagos.",
    405: "Metodo no permitido en esta ruta.",
}


def _respuesta(cuerpo: dict, estado: int):
    return jsonify({"error": cuerpo}), estado


def registrar_manejadores(app) -> None:

    @app.errorhandler(ErrorDePagos)
    def error_de_pagos(error: ErrorDePagos):
        logger.info("Peticion rechazada: [%s] %s", error.codigo, error)
        return _respuesta(error.como_diccionario(), error.estado_http)

    @app.errorhandler(HTTPException)
    def error_http(error: HTTPException):
        cuerpo = {
            "codigo": f"HTTP-{error.code}",
            "mensaje": MENSAJES_HTTP.get(error.code, error.description),
        }
        return _respuesta(cuerpo, error.code)

    @app.errorhandler(Exception)
    def error_inesperado(error: Exception):
        # El detalle va al log, nunca al cliente.
        logger.exception("Error no controlado en el servicio de pagos")
        cuerpo = {
            "codigo": "HTTP-500",
            "mensaje": "Error interno del servicio de pagos.",
        }
        return _respuesta(cuerpo, 500)
