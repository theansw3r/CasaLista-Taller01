from django.utils.translation import gettext as _
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as manejador_de_drf

from apps.comun.dominio.excepciones import ErrorDeDominio

logger = logging.getLogger(__name__)

CODIGO_HTTP_GENERICO = "HTTP-{estado}"


def manejar_excepcion(excepcion, contexto):
    if isinstance(excepcion, ErrorDeDominio):
        return _respuesta_de_dominio(excepcion, contexto)

    respuesta = manejador_de_drf(excepcion, contexto)
    if respuesta is None:
        return None
    return _normalizar_respuesta_de_drf(respuesta)


def _respuesta_de_dominio(excepcion: ErrorDeDominio, contexto) -> Response:
    vista = contexto.get("view").__class__.__name__ if contexto.get("view") else "?"
    logger.info(
        "Regla de negocio rechazada en %s: [%s] %s",
        vista,
        excepcion.codigo,
        excepcion,
    )
    return Response(
        {"error": excepcion.como_diccionario()},
        status=excepcion.estado_http,
    )


def _normalizar_respuesta_de_drf(respuesta: Response) -> Response:
    detalle = respuesta.data
    if isinstance(detalle, dict) and "error" in detalle:
        return respuesta

    error = {
        "codigo": CODIGO_HTTP_GENERICO.format(estado=respuesta.status_code),
        "mensaje": _mensaje_legible(detalle),
    }
    if isinstance(detalle, dict):
        error["contexto"] = {"campos": detalle}

    respuesta.data = {"error": error}
    return respuesta


def _mensaje_legible(detalle) -> str:
    if isinstance(detalle, dict):
        if "detail" in detalle:
            return str(detalle["detail"])
        return _("La peticion tiene campos invalidos.")
    if isinstance(detalle, list) and detalle:
        return str(detalle[0])
    return str(detalle)
