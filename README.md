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

## Dónde ver la API

- `http://localhost:8000/api/docs/` — Swagger
- `http://localhost:8000/api/v1/salud/`
- `http://localhost:8000/admin/` — para verificar profesionales (`createsuperuser`)

## Estructura

```
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

Documentación más detallada en [`docs/wiki/`](docs/wiki):

- [Estructura de carpetas](docs/wiki/01-Estructura-de-Carpetas.md)
- [Diagrama de secuencia](docs/wiki/02-Diagrama-de-Secuencia.md)
- [Preparación para API Gateway](docs/wiki/03-API-Gateway.md)

## Cambiar comportamiento sin tocar código

Tres variables en `.env` controlan qué implementación usan las Factories:

| Variable | Valores | Qué cambia |
|---|---|---|
| `NOTIFICADOR_TYPE` | `MOCK` / `REAL` | log en consola / correo real |
| `TARIFA_TYPE` | `BASE` / `DINAMICA` | precio normal / con recargo nocturno y fin de semana |
| `PASARELA_PAGO_TYPE` | `SIMULADA` / `TARJETA` / `PSE` | siempre aprueba / adaptador real |
