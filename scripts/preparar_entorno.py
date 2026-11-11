"""Crea .env local sin imprimir secretos ni sobrescribir configuración existente."""

import os
import secrets
from pathlib import Path

if __name__ == "__main__":
    plantilla = Path(".env.example").read_text()
    valores = {
        "DJANGO_SECRET_KEY": secrets.token_hex(32),
        "TOKEN_SERVICIO_PAGOS": secrets.token_hex(32),
        "DB_PASSWORD": secrets.token_hex(24),
    }
    lineas = []
    for linea in plantilla.splitlines():
        clave = linea.split("=", 1)[0]
        lineas.append(f"{clave}={valores[clave]}" if clave in valores else linea)
    fd = os.open(".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as archivo:
        archivo.write("\n".join(lineas) + "\n")
    print(".env creado con permisos privados. No lo suba al repositorio.")
