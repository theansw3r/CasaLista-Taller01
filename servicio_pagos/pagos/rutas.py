from datetime import timezone

from flask import Blueprint, current_app, g, jsonify, request

from pagos.errores import DatosInvalidos, SinCredenciales
from pagos.servicio import (
    ConsultaPagosService,
    PagoService,
    ProcesarPagoCommand,
    SaludService,
    a_dinero,
)

bp = Blueprint("pagos", __name__, url_prefix="/api/v2/pagos")

MEDIOS = ("TARJETA", "PSE")


@bp.post("/")
def procesar_pago():
    autorizacion = _exigir_token()
    reserva_id, medio = _leer_cuerpo(request.get_json(silent=True))
    servicio = PagoService(
        reservas=current_app.extensions["cliente_reservas"],
        configuracion_pasarela=current_app.config["PASARELA_PAGO_TYPE"],
    )
    pago, estado_reserva = servicio.procesar(
        ProcesarPagoCommand(
            reserva_id=reserva_id,
            medio=medio,
            autorizacion=autorizacion,
            id_peticion=g.id_peticion,
        )
    )
    return jsonify(_pago_a_json(pago, estado_reserva)), 201


@bp.get("/<int:pago_id>/")
def detalle_pago(pago_id: int):
    autorizacion = _exigir_token()
    servicio = ConsultaPagosService(current_app.extensions["cliente_reservas"])
    pago, estado_reserva = servicio.detalle_de(pago_id, autorizacion, g.id_peticion)
    return jsonify(_pago_a_json(pago, estado_reserva)), 200


@bp.get("/salud/")
def salud():
    reporte, viva = SaludService().estado()
    reporte["id_peticion"] = g.id_peticion
    return jsonify(reporte), 200 if viva else 503


def _exigir_token() -> str:
    autorizacion = request.headers.get("Authorization", "")
    if not autorizacion.startswith("Bearer "):
        raise SinCredenciales()
    return autorizacion


def _leer_cuerpo(cuerpo) -> tuple[int, str]:
    if not isinstance(cuerpo, dict):
        raise DatosInvalidos("El cuerpo de la peticion debe ser un objeto JSON.")

    errores = {}
    reserva_id = cuerpo.get("reserva_id")
    if isinstance(reserva_id, bool) or not isinstance(reserva_id, int) or reserva_id < 1:
        errores["reserva_id"] = ["Debe ser un numero entero mayor o igual a 1."]
    medio = cuerpo.get("medio")
    if medio not in MEDIOS:
        errores["medio"] = [f"Debe ser uno de: {', '.join(MEDIOS)}."]

    if errores:
        raise DatosInvalidos(campos=errores)
    return reserva_id, medio


def _pago_a_json(pago, estado_reserva: str) -> dict:
    # Mismos campos que PagoSerializer en Django (v1). Asi el front no tiene
    # que cambiar nada salvo la URL.
    return {
        "id": pago.id,
        "reserva_id": pago.reserva_id,
        "estado_reserva": estado_reserva,
        "monto": str(a_dinero(pago.monto)),
        "medio": pago.medio,
        "estado": pago.estado,
        "pasarela": pago.pasarela,
        "referencia_externa": pago.referencia_externa,
        "creado_en": _iso(pago.creado_en),
    }


def _iso(momento) -> str:
    # SQLite devuelve la fecha sin zona; se guardo en UTC.
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.isoformat()
