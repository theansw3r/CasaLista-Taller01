"""
Traductor unico de excepciones a respuestas HTTP.

Este archivo es la razon por la que en `views.py` no hay un solo `try/except`.
DRF llama a `manejar_excepcion` cada vez que una vista levanta algo, asi que
basta con que el dominio lance su excepcion y aqui se decide el codigo de
estado y el formato del cuerpo.

Beneficios concretos:

* Las vistas quedan en 5-6 lineas y sin conocimiento de reglas.
* Todos los errores de la API tienen la MISMA forma, venga el error del
  dominio, de un serializer o de DRF. Un cliente (o el API Gateway) puede
  parsear un solo formato.
* Agregar una regla de negocio nueva no obliga a tocar la capa de API.

Formato de la respuesta de error:

    {
      "error": {
        "codigo": "RN-01",
        "mensaje": "La franja horaria ya fue tomada.",
        "contexto": {...}          # opcional
      }
    }
"""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as manejador_de_drf

from apps.comun.dominio.excepciones import ErrorDeDominio

logger = logging.getLogger(__name__)

# Codigo que se reporta cuando el error lo genero DRF y no el dominio.
CODIGO_HTTP_GENERICO = "HTTP-{estado}"


def manejar_excepcion(excepcion, contexto):
    """Punto de entrada configurado en REST_FRAMEWORK["EXCEPTION_HANDLER"]."""
    if isinstance(excepcion, ErrorDeDominio):
        return _respuesta_de_dominio(excepcion, contexto)

    respuesta = manejador_de_drf(excepcion, contexto)
    if respuesta is None:
        # No es un error controlado: es un bug. Se deja subir para que Django
        # lo registre como 500 y no se disfrace de error de negocio.
        return None
    return _normalizar_respuesta_de_drf(respuesta)


def _respuesta_de_dominio(excepcion: ErrorDeDominio, contexto) -> Response:
    """Convierte una excepcion del dominio en su respuesta HTTP."""
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
    """Envuelve los errores propios de DRF en el mismo formato del dominio.

    Los errores de validacion de un serializer llegan como
    {"campo": ["mensaje"]}; se conservan dentro de `contexto` para que el
    cliente sepa exactamente que campo corregir, pero la forma externa de la
    respuesta sigue siendo la misma que la de un error de dominio.
    """
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
    """Saca un texto corto de la estructura de errores de DRF."""
    if isinstance(detalle, dict):
        if "detail" in detalle:
            return str(detalle["detail"])
        return "La peticion tiene campos invalidos."
    if isinstance(detalle, list) and detalle:
        return str(detalle[0])
    return str(detalle)
