#!/usr/bin/env python
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
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
