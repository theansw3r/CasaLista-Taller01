"""Pruebas HTTP por Nginx. No imprime JWT ni usa datos personales reales."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://localhost:8080")
parser.add_argument("--datos-demo-locales", action="store_true")
parser.add_argument("--salida", default=".evidencias-locales/http.json")
args = parser.parse_args()
s = requests.Session()
s.headers["Accept-Language"] = "en"
reporte = {"fecha_utc": datetime.now(UTC).isoformat(), "base": args.base, "pruebas": []}


def comprobar(ruta, codigo=200, metodo="GET", **kwargs):
    r = s.request(metodo, args.base + ruta, timeout=20, **kwargs)
    assert r.status_code == codigo, (ruta, r.status_code, r.text[:200])
    dato = r.json() if "application/json" in r.headers.get("Content-Type", "") else None
    reporte["pruebas"].append(
        {
            "ruta": ruta,
            "metodo": metodo,
            "http": r.status_code,
            "id_peticion": r.headers.get("X-Request-ID"),
        }
    )
    return dato


comprobar("/api/v1/salud/")
comprobar("/api/v2/pagos/salud/")
comprobar("/interno/reservas/1/confirmacion/", 404)
comprobar("/api/v2/pagos/", 401, "POST", json={})
catalogo = comprobar("/api/v1/catalogo/profesionales/")
assert isinstance(catalogo["resultados"], list)
clima = comprobar("/api/v1/integraciones/clima/")
assert clima["fuente"] == "Open-Meteo"
reporte["clima_real"] = clima
aliado = comprobar("/api/v1/integraciones/aliado/", 503)
assert aliado["error"]["codigo"] == "ALIADO-PENDIENTE"

if args.datos_demo_locales:
    assert urlparse(args.base).hostname in ["localhost", "127.0.0.1"], (
        "La creación automática de demo se limita a localhost"
    )
    datos = comprobar(
        "/api/v1/cuentas/token/",
        200,
        "POST",
        json={"username": "laura@correo.com", "password": "casalista2026"},
    )
    s.headers["Authorization"] = "Bearer " + datos["access"]
    profesional = catalogo["resultados"][0]["id"]
    servicios = comprobar(f"/api/v1/catalogo/profesionales/{profesional}/servicios/")[
        "resultados"
    ]
    bloques = comprobar(
        f"/api/v1/reservas/disponibilidad/?profesional_id={profesional}"
    )["resultados"]
    assert bloques, "Se requiere un bloque libre de demo"
    reserva = comprobar(
        "/api/v1/reservas/",
        201,
        "POST",
        json={
            "bloque_id": bloques[0]["id"],
            "direccion": "Dirección de demostración",
            "zona": "Laureles",
            "servicios": [{"servicio_id": servicios[0]["id"], "cantidad": 1}],
        },
    )
    pago = comprobar(
        "/api/v2/pagos/",
        201,
        "POST",
        json={"reserva_id": reserva["id"], "medio": "TARJETA"},
    )
    assert pago["pasarela"] == "SIMULADA" and pago["estado_reserva"] == "CONFIRMADA"
    comprobar(
        "/api/v2/pagos/",
        409,
        "POST",
        json={"reserva_id": reserva["id"], "medio": "TARJETA"},
    )
    reporte["reserva_demo_id"] = reserva["id"]
    reporte["pago_demo_id"] = pago["id"]
    # No se registran direcciones, nombres, JWT o detalles de cuenta en evidencia.

p = Path(args.salida)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n")
print(
    f"{len(reporte['pruebas'])} comprobaciones HTTP correctas; evidencia guardada en {p}"
)
