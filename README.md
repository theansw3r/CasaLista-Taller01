# CasaLista — Entrega 1

Marketplace de reserva de servicios para el hogar. Entrega 1 de Arquitectura
de Software: núcleo de negocio + API con Django REST Framework.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env        # Linux/macOS: cp .env.example .env

python manage.py migrate
python manage.py sembrar_demo
python manage.py runserver
```

`sembrar_demo` crea un profesional verificado, catálogo, agenda y hace una
reserva de ejemplo (usa los mismos servicios que la API, no crea nada a
mano).

```bash
python manage.py test    # corre las pruebas
```

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
  pagos/       # Pago  (acá está la Factory de pasarelas)
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
| `NOTIFICADOR_TYPE` | `MOCK` / `REAL` | log en consola / correo real |
| `TARIFA_TYPE` | `BASE` / `DINAMICA` | precio normal / con recargo nocturno y fin de semana |
| `PASARELA_PAGO_TYPE` | `SIMULADA` / `TARJETA` / `PSE` | siempre aprueba / adaptador real |
