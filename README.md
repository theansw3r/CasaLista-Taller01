# CasaLista - Taller 01

Marketplace de reserva de servicios para el hogar.

Refactorizacion del flujo **Crear Reserva**: la logica sale de la vista y queda
repartida en Service Layer, Builder (dominio) y Factory (infraestructura).

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

## Uso

```bash
python manage.py test reservas    # pruebas
python manage.py sembrar_demo     # crea datos y una reserva de ejemplo
```

## Variables de entorno

Las Factories eligen la implementacion segun el entorno (ver `.env.example`):

| Variable | Valores | Efecto |
|---|---|---|
| `NOTIFICADOR_TYPE` | `MOCK` / `REAL` | imprime en consola / envia correo |
| `TARIFA_TYPE` | `BASE` / `DINAMICA` | suma simple / recargo nocturno y fin de semana |

```bash
$env:NOTIFICADOR_TYPE="MOCK"; $env:TARIFA_TYPE="BASE";     python manage.py sembrar_demo
$env:NOTIFICADOR_TYPE="REAL"; $env:TARIFA_TYPE="DINAMICA"; python manage.py sembrar_demo
```

## Paginas

| Ruta | Que hace |
|---|---|
| `/` | inicio |
| `/cuentas/registro/` | registro de un cliente nuevo |
| `/cuentas/login/` `/cuentas/logout/` | sesion |
| `/mis-reservas/` | reservas del cliente autenticado |
| `POST /api/reservas/` | crea una reserva (endpoint JSON) |

