"""Extrae, verifica y compila catálogos gettext sin depender de binarios del SO.

Uso: python scripts/catalogos.py --extraer (lista faltantes)
     python scripts/catalogos.py (verificación estricta + .mo)
Requiere requirements-dev.txt. Nunca inventa traducciones faltantes.
"""
import ast
import re
import shutil
import sys
from pathlib import Path

import polib
from babel.messages.extract import extract_javascript

RAIZ = Path(__file__).resolve().parent.parent

def mensajes():
    dominios = {'django': set(), 'djangojs': set()}
    archivos = list((RAIZ/'apps').rglob('*.py')) + list((RAIZ/'servicio_pagos/pagos').glob('*.py'))
    for archivo in archivos:
        if any(p in archivo.parts for p in ('migrations', 'tests', 'management')) or archivo.name.startswith('test'): continue
        for nodo in ast.walk(ast.parse(archivo.read_text())):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in ('_', '_lazy', 'gettext', 'marcar'):
                if nodo.args and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str): dominios['django'].add(nodo.args[0].value)
    for archivo in (RAIZ/'templates').glob('*.html'):
        for a,b in re.findall(r'''{%\s*translate\s+(?:"([^"]*)"|'([^']*)')\s*%}''', archivo.read_text()): dominios['django'].add(a or b)
    for archivo in (RAIZ/'static/js').glob('*.js'):
        with archivo.open('rb') as f:
            for _, _, msg, _ in extract_javascript(f, ['gettext', 'ngettext'], [], {"parse_template_string": True}):
                if isinstance(msg, str): dominios['djangojs'].add(msg)
    # Valores de contrato: no cambian las claves/códigos que usa el cliente.
    dominios['djangojs'].update(['PENDIENTE', 'CONFIRMADA', 'COMPLETADA', 'CANCELADA', 'LIBRE', 'OCUPADO', 'ACTIVO', 'INACTIVO', 'BASE', 'DINAMICA'])
    return dominios

if __name__ == '__main__':
    faltantes=[]
    for dominio, claves in mensajes().items():
        destino=RAIZ/'locale/en/LC_MESSAGES'/f'{dominio}.po'
        po=polib.pofile(str(destino)) if destino.exists() else polib.POFile()
        po.metadata={'Project-Id-Version':'CasaLista Entrega 2','Language':'en','Content-Type':'text/plain; charset=UTF-8','Plural-Forms':'nplurals=2; plural=(n != 1);'}
        for clave in sorted(claves):
            entrada=po.find(clave)
            if entrada is None: entrada=polib.POEntry(msgid=clave);po.append(entrada)
            if not entrada.msgstr or 'fuzzy' in entrada.flags:
                faltantes.append((dominio,clave))
            elif sorted(re.findall(r'%\([^)]+\)[a-z]', clave)) != sorted(re.findall(r'%\([^)]+\)[a-z]', entrada.msgstr)):
                raise ValueError(f"Placeholders de traducción inconsistentes: {clave}")
        destino.parent.mkdir(parents=True,exist_ok=True);po.save(str(destino))
        if not faltantes: po.save_as_mofile(str(destino.with_suffix('.mo')))
    if faltantes:
        import json
        print(json.dumps(faltantes,ensure_ascii=False,indent=2))
        sys.exit(0 if '--extraer' in sys.argv else 1)
    for idioma in ['en']:
        destino=RAIZ/'servicio_pagos/locale'/idioma/'LC_MESSAGES';destino.mkdir(parents=True,exist_ok=True)
        shutil.copy2(RAIZ/'locale'/idioma/'LC_MESSAGES/django.mo',destino/'django.mo')
    print('Catálogos completos y compilados; español usa los msgid de origen.')
