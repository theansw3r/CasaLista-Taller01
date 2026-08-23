#!/usr/bin/env python
"""Punto de entrada de las tareas administrativas de Django."""

import os
import sys
from pathlib import Path

# Se carga el .env (si existe) ANTES de importar settings, porque settings lee
# las variables de entorno en tiempo de import.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    # Sin python-dotenv el proyecto sigue funcionando: solo hay que exportar
    # las variables a mano. No vale la pena romper aqui por esto.
    pass


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        raise ImportError(
            "No se pudo importar Django. Active el entorno virtual e instale "
            "las dependencias con: pip install -r requirements.txt"
        ) from error
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
