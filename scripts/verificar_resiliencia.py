"""Ensayo de fallos EXCLUSIVO del proyecto local de validación."""

import json
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

PROYECTO = "casalista-entrega2-validacion"
COMPOSE = ["docker", "compose", "-p", PROYECTO]
BASE = "http://localhost:8080"


def docker(*args):
    return subprocess.run(
        COMPOSE + list(args), check=True, capture_output=True, text=True
    ).stdout


def api(s, ruta, metodo="GET", codigo=200, **kw):
    r = s.request(metodo, BASE + ruta, timeout=20, **kw)
    assert r.status_code == codigo, (ruta, r.status_code)
    return r.json()


def sesion(correo):
    s = requests.Session()
    s.headers["Accept-Language"] = "en"
    token = api(
        s,
        "/api/v1/cuentas/token/",
        "POST",
        json={"username": correo, "password": "casalista2026"},
    )["access"]
    s.headers["Authorization"] = "Bearer " + token
    return s


def evento(reserva):
    codigo = f'from apps.reservas.models import NotificacionPendiente; import json; e=NotificacionPendiente.objects.get(reserva_id={reserva}); print(json.dumps({{"id":e.pk,"enviada":e.enviada_en is not None,"idioma":e.idioma}}))'
    return json.loads(
        docker("exec", "-T", "django", "python", "manage.py", "shell", "-c", codigo)
        .strip()
        .splitlines()[-1]
    )


reporte = {
    "fecha_utc": datetime.now(UTC).isoformat(),
    "ambiente": "local aislado",
    "proyecto": PROYECTO,
}
cliente = sesion("laura@correo.com")
pro = sesion("andres.plomeria@casalista.co")
perfil = api(pro, "/api/v1/cuentas/perfil/")["profesional"]["id"]
inicio = (datetime.now(UTC) + timedelta(days=30)).replace(microsecond=0)
bloque = api(
    pro,
    "/api/v1/reservas/disponibilidad/",
    "POST",
    201,
    json={
        "inicio": inicio.isoformat(),
        "fin": (inicio + timedelta(hours=2)).isoformat(),
    },
)
servicio = api(cliente, f"/api/v1/catalogo/profesionales/{perfil}/servicios/")[
    "resultados"
][0]["id"]

try:
    docker("stop", "redis")
    antes = time.monotonic()
    reserva = api(
        cliente,
        "/api/v1/reservas/",
        "POST",
        201,
        json={
            "bloque_id": bloque["id"],
            "direccion": "Prueba local de recuperación",
            "zona": "Laureles",
            "servicios": [{"servicio_id": servicio, "cantidad": 1}],
        },
    )
    reporte["reserva_sin_redis"] = {
        "http": 201,
        "id": reserva["id"],
        "segundos": round(time.monotonic() - antes, 2),
        "evento": evento(reserva["id"]),
    }
    assert not reporte["reserva_sin_redis"]["evento"]["enviada"]
    assert api(cliente, "/api/v1/salud/")["base_de_datos"] == "ok"
finally:
    docker("start", "redis")
# Ejecutar la misma tarea de recuperación del scheduler para no esperar 60 s.
docker(
    "exec",
    "-T",
    "django",
    "python",
    "manage.py",
    "shell",
    "-c",
    "from apps.reservas.tasks import recuperar_notificaciones; recuperar_notificaciones.delay()",
)
for _ in range(30):
    estado = evento(reserva["id"])
    if estado["enviada"]:
        break
    time.sleep(1)
assert estado["enviada"], "El worker no recuperó el evento"
reporte["recuperado"] = estado
try:
    docker("stop", "pagos")
    caida = api(cliente, "/api/v2/pagos/salud/", codigo=503)
    assert caida["error"]["codigo"] == "HTTP-503"
    api(cliente, "/api/v1/salud/")
    reporte["flask_caido"] = {
        "pagos_http": 503,
        "django_http": 200,
        "mensaje": caida["error"]["mensaje"],
    }
finally:
    docker("start", "pagos")
for _ in range(20):
    r = cliente.get(BASE + "/api/v2/pagos/salud/", timeout=5)
    if r.status_code == 200:
        break
    time.sleep(1)
assert r.status_code == 200
reporte["flask_recuperado_http"] = 200
salida = Path(".evidencias-locales/resiliencia.json")
salida.parent.mkdir(parents=True, exist_ok=True)
salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n")
print(
    "Reserva conservada sin Redis, evento recuperado y aislamiento de caída Flask verificados."
)
