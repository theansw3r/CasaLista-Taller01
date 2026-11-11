"""gettext por petición, sin compartir estado de idioma entre workers."""

import gettext as catalogos
from pathlib import Path

from flask import has_request_context, request

LOCALE = Path(__file__).resolve().parent.parent / "locale"
CATALOGOS = {
    idioma: catalogos.translation(
        "django", localedir=LOCALE, languages=[idioma], fallback=True
    )
    for idioma in ("es", "en")
}


def marcar(mensaje):
    # Marcador de extracción para atributos de clase; se traduce al crear el error.
    return mensaje


def gettext(mensaje):
    idioma = (
        request.headers.get("Accept-Language", "es") if has_request_context() else "es"
    )
    elegido = "en" if idioma.lower().startswith("en") else "es"
    return CATALOGOS[elegido].gettext(mensaje)
