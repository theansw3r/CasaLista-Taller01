"""Extrae, verifica y compila los catalogos gettext (ES -> EN).

No usa makemessages porque ese comando necesita los binarios de GNU gettext,
que no vienen en Windows. Este script solo depende de requirements-dev.txt.

Uso:
    python scripts/catalogos.py --extraer   agrega al .po los textos nuevos y
                                            lista los que faltan por traducir
    python scripts/catalogos.py             falla si falta alguna traduccion;
                                            si esta todo, compila los .mo

Nunca inventa traducciones. Los textos que ya no aparecen en el codigo quedan
marcados como obsoletos (#~) para no cargar basura en el .mo.
"""

import ast
import json
import re
import shutil
import sys
from pathlib import Path

import polib
from babel.messages.extract import extract_javascript

RAIZ = Path(__file__).resolve().parent.parent
IDIOMAS = ["en"]

FUNCIONES_GETTEXT_PY = {"_", "_lazy", "gettext", "marcar"}
FUNCIONES_GETTEXT_JS = ["gettext", "ngettext"]
CARPETAS_IGNORADAS = {"migrations", "tests", "management"}
PLANTILLA_TRANSLATE = re.compile(
    r"""{%\s*translate\s+(?:"([^"]*)"|'([^']*)')\s*%}"""
)
MARCADOR = re.compile(r"%\([^)]+\)[a-z]")

# Valores de contrato de la API: el front los traduce para mostrarlos, pero
# no aparecen como texto literal dentro de gettext().
VALORES_DE_CONTRATO_JS = {
    "PENDIENTE",
    "CONFIRMADA",
    "COMPLETADA",
    "CANCELADA",
    "LIBRE",
    "OCUPADO",
    "ACTIVO",
    "INACTIVO",
    "BASE",
    "DINAMICA",
}


def _leer(archivo: Path) -> str:
    return archivo.read_text(encoding="utf-8")


def _archivos_python():
    fuentes = list((RAIZ / "apps").rglob("*.py"))
    fuentes += list((RAIZ / "servicio_pagos/pagos").glob("*.py"))
    for archivo in fuentes:
        if CARPETAS_IGNORADAS & set(archivo.parts) or archivo.name.startswith("test"):
            continue
        yield archivo


def _textos_python(archivo: Path):
    for nodo in ast.walk(ast.parse(_leer(archivo))):
        if not (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id in FUNCIONES_GETTEXT_PY
            and nodo.args
            and isinstance(nodo.args[0], ast.Constant)
            and isinstance(nodo.args[0].value, str)
        ):
            continue
        yield nodo.args[0].value


def _textos_plantilla(archivo: Path):
    for doble, simple in PLANTILLA_TRANSLATE.findall(_leer(archivo)):
        yield doble or simple


def _textos_javascript(archivo: Path):
    with archivo.open("rb") as contenido:
        opciones = {"parse_template_string": True}
        for _linea, _funcion, mensaje, _comentarios in extract_javascript(
            contenido, FUNCIONES_GETTEXT_JS, [], opciones
        ):
            if isinstance(mensaje, str):
                yield mensaje


def mensajes() -> dict[str, set[str]]:
    django = set()
    for archivo in _archivos_python():
        django.update(_textos_python(archivo))
    for archivo in (RAIZ / "templates").glob("*.html"):
        django.update(_textos_plantilla(archivo))

    javascript = set(VALORES_DE_CONTRATO_JS)
    for archivo in (RAIZ / "static/js").glob("*.js"):
        javascript.update(_textos_javascript(archivo))

    return {"django": django, "djangojs": javascript}


def _sincronizar(po: polib.POFile, claves: set[str]) -> list[str]:
    """Agrega los textos nuevos, marca los viejos y devuelve los que faltan."""
    faltantes = []
    for clave in sorted(claves):
        entrada = po.find(clave, include_obsolete_entries=True)
        if entrada is None:
            entrada = polib.POEntry(msgid=clave)
            po.append(entrada)
        entrada.obsolete = False

        if not entrada.msgstr or "fuzzy" in entrada.flags:
            faltantes.append(clave)
        elif sorted(MARCADOR.findall(clave)) != sorted(
            MARCADOR.findall(entrada.msgstr)
        ):
            raise ValueError(f"Marcadores distintos en la traduccion de: {clave!r}")

    for entrada in po:
        if entrada.msgid not in claves:
            entrada.obsolete = True
    return faltantes


def main(solo_extraer: bool) -> int:
    faltantes = []
    catalogos = []
    for idioma in IDIOMAS:
        for dominio, claves in mensajes().items():
            ruta = RAIZ / "locale" / idioma / "LC_MESSAGES" / f"{dominio}.po"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            po = polib.pofile(str(ruta)) if ruta.exists() else polib.POFile()
            po.metadata = {
                "Project-Id-Version": "CasaLista",
                "Language": idioma,
                "Content-Type": "text/plain; charset=UTF-8",
                "Plural-Forms": "nplurals=2; plural=(n != 1);",
            }
            pendientes = _sincronizar(po, claves)
            po.save(str(ruta))
            faltantes += [(idioma, dominio, clave) for clave in pendientes]
            catalogos.append((po, ruta))

    if faltantes:
        print(json.dumps(faltantes, ensure_ascii=False, indent=2))
        return 0 if solo_extraer else 1

    for po, ruta in catalogos:
        po.save_as_mofile(str(ruta.with_suffix(".mo")))

    # Flask usa el mismo catalogo del servidor (no tiene textos de JS).
    for idioma in IDIOMAS:
        destino = RAIZ / "servicio_pagos/locale" / idioma / "LC_MESSAGES"
        destino.mkdir(parents=True, exist_ok=True)
        origen = RAIZ / "locale" / idioma / "LC_MESSAGES" / "django.mo"
        shutil.copy2(origen, destino / "django.mo")

    print("Catalogos completos y compilados; el espanol usa los msgid de origen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(solo_extraer="--extraer" in sys.argv))
