# CasaLista

Marketplace de reserva de servicios para el hogar. Arquitectura de Software:
núcleo de negocio + API con Django REST Framework (Entrega 1), y el módulo de
pagos migrado a un microservicio en Flask con el patrón Strangler (Taller 2).

## Entrega 2

Desplegado en AWS Academy: **http://52.2.74.242** (EC2 con IP elástica).

Incluye Redis/Celery con outbox transaccional, consumo de Open-Meteo mediante
Adapter e inversión de dependencias, interfaz renovada y traducción ES/EN con
gettext. El consumo del servicio del equipo aliado queda pendiente.

Toda la documentación de la entrega está en la Wiki:
[Entrega 2](https://github.com/theansw3r/CasaLista-Taller01/wiki/Entrega-2).

## Con Docker Compose

Para una instalación nueva (Python 3 para generar secretos, Docker Engine y Compose):

```bash
python3 scripts/preparar_entorno.py
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
```

El generador no sobrescribe .env. Si actualiza una instalación existente,
conserve credenciales y volúmenes; consulte la guía de despliegue antes de cambiar
contraseñas. Los contenedores no publican base de datos ni Redis.
La aplicación local está en http://localhost:8080/; Nginx publica solo loopback.

Solo para una instalación con datos ficticios de demostración:

```bash
docker compose exec django python manage.py sembrar_demo
```

| Ruta | Servicio |
|---|---|
| `/api/v2/pagos/` | Flask, pagos simulados |
| `/api/v1/...`, `/admin/`, `/`, `/i18n/`, `/jsi18n/` | Django |
| `/api/v1/integraciones/clima/` | Django, Adapter de Open-Meteo real |
| `/api/v1/integraciones/aliado/` | 503: falta equipo/contrato |
| `/interno/...` | 404 público; comunicación directa entre servicios |

Celery procesa notificaciones después del commit; Beat recupera eventos
pendientes cada minuto. El backend de correo es consola por defecto: no envía
correos externos. Las traducciones compiladas se incluyen en ambas imágenes.

## Desarrollo y pruebas

Python 3.12, con entorno virtual aislado:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt -r servicio_pagos/requirements-dev.txt
python scripts/preparar_entorno.py
python scripts/catalogos.py
python manage.py migrate
python manage.py test
python -m pytest servicio_pagos -q
python manage.py runserver
```

En Windows use `.venv\Scripts\activate`. Con runserver se conserva SQLite y
pagos v1; Compose usa PostgreSQL y Flask v2. La validación de filas concurrentes
requiere PostgreSQL. No usar SQLite como prueba de bloqueo distribuido.

Pruebas de integración sobre una instalación local de demo ya iniciada:

```bash
python scripts/verificar_http.py --datos-demo-locales
```

`scripts/verificar_resiliencia.py` detiene/recupera servicios exclusivamente en
el proyecto Compose `casalista-entrega2-validacion`. No usarlo en AWS.
Para agregar textos, marcarlos con gettext, ejecutar
`python scripts/catalogos.py --extraer`, traducir las entradas PO y compilar
con `python scripts/catalogos.py`; falla si falta alguna traducción.

## Usar la aplicación

Con el servidor corriendo, entra a `http://localhost:8000/`. Ahí está la
interfaz: iniciar sesión, buscar un profesional por zona, elegir servicios y
horario, reservar, pagar y cancelar.

Credenciales de prueba (las crea `sembrar_demo`):
`laura@correo.com` / `casalista2026`

Hay dos tipos de cuenta: **cliente** (busca y reserva) y **profesional**
(publica servicios y horarios). El menú cambia según el rol.

El front end es HTML + JavaScript sin librerías, y consume la API por `fetch`.
No ejecuta ninguna regla de negocio: todo lo decide el backend, y cuando una
regla falla la interfaz muestra el código correspondiente (RN-01, RN-07...).

### Qué se puede publicar

CasaLista no es un marketplace de servicios en general.el catálogo se limita a **cinco oficios** de visita corta:
plomería, electricidad, reparación de electrodomésticos, pintura y cerrajería.
Además, cada visita debe durar **entre 1 y 4 horas**, y el servicio tiene que
venir descrito.

Esas reglas las hace cumplir `apps/catalogo/dominio/estandares.py`, no el
formulario: publicar algo fuera del nicho devuelve `400` con el código
`CAT-05`.

Otras rutas:

- `http://localhost:8000/api/` — lista los endpoints
- `http://localhost:8000/api/v1/salud/`
- `http://localhost:8000/admin/` — para verificar profesionales (`createsuperuser`)

## Estructura

```
templates/     # la interfaz (index.html)
static/        # css y javascript del front end
apps/
  comun/       # cosas compartidas (dinero, errores, factory base)
  cuentas/     # Usuario, Cliente, Profesional
  catalogo/    # Servicio
  reservas/    # BloqueDisponibilidad, Reserva, DetalleReserva  (acá está el Builder)
  pagos/       # Pago  (legacy, /api/v1/pagos/)
  integraciones/  # Adapter de Open-Meteo y consumo del equipo aliado
servicio_pagos/  # microservicio Flask que reemplaza a apps/pagos (/api/v2/pagos/)
nginx/           # nginx.conf: reparte el tráfico entre Django y Flask
docker/          # script que crea la base de datos de pagos en Postgres
```

Cada app tiene: `models.py` (solo datos), `dominio/` (reglas de negocio y el
Builder), `services.py` (un caso de uso por clase), `infraestructura/`
(Factories y adaptadores) y `api/` (serializers + views + urls).

La documentación técnica (estructura de carpetas, diagrama de secuencia y
preparación para API Gateway) está en la Wiki del repositorio.

## Cambiar comportamiento sin tocar código

Tres variables en `.env` controlan qué implementación usan las Factories:

| Variable | Valores | Qué cambia |
|---|---|---|
| `NOTIFICADOR_TYPE` | `MOCK` / `REAL` / `ASYNC` | log / correo síncrono / outbox + Celery |
| `TARIFA_TYPE` | `BASE` / `DINAMICA` | precio normal / con recargo nocturno y fin de semana |
| `PASARELA_PAGO_TYPE` | `SIMULADA` / `TARJETA` / `PSE` | simulaciones locales; no efectúan cobros reales |
