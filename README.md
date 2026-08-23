# CasaLista — Entrega 1

Marketplace de reserva de servicios profesionales para el hogar en el Área
Metropolitana del Valle de Aburrá.

**Entrega No. 1: Núcleo de Negocio y Exposición de API Profesional**
Arquitectura de Software 2026 — Prof. Nicolás Ramírez Vélez

La documentación técnica completa está en [`docs/wiki/`](docs/wiki) y en la
Wiki del repositorio.

---

## Qué se implementó

| Requisito de la entrega | Dónde está |
|---|---|
| 50–60 % de las clases de dominio | 8 de 10 clases del diagrama (80 %) — ver [Modelo de Dominio](docs/wiki/01-Modelo-de-Dominio.md) |
| Service Layer, sin lógica en views ni serializers | un `services.py` por app — ver [Arquitectura por Capas](docs/wiki/03-Arquitectura-por-Capas.md) |
| Serializers + `APIView` + códigos HTTP | `apps/*/api/` — ver [Referencia de la API](docs/wiki/07-Referencia-de-la-API.md) |
| **Builder** en la entidad más compleja | `apps/reservas/dominio/reserva_builder.py` |
| **Factory** para dependencia externa y variante de lógica | 3 factories — ver [Patrones Creacionales](docs/wiki/04-Patrones-Creacionales.md) |
| Preparación para API Gateway | ver [API Gateway](docs/wiki/06-API-Gateway.md) |

127 pruebas automáticas cubren las reglas de negocio, la orquestación de los
servicios y los códigos de estado de la API.

---

## Instalación

Requiere Python 3.11 o superior.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # copy .env.example .env en Windows

python manage.py migrate
python manage.py sembrar_demo
python manage.py runserver
```

`sembrar_demo` crea un profesional verificado con catálogo y agenda, un
cliente, y ejecuta el flujo completo (reserva → pago → confirmación) usando
los mismos servicios que usa la API.

### Comprobar que todo funciona

```bash
python manage.py test          # 127 pruebas
```

---

## Puntos de entrada

| URL | Qué es |
|---|---|
| `http://localhost:8000/api/docs/` | documentación interactiva (Swagger) |
| `http://localhost:8000/api/schema/` | contrato OpenAPI que consume el Gateway |
| `http://localhost:8000/api/v1/salud/` | estado de la instancia |
| `http://localhost:8000/admin/` | panel para verificar profesionales (RN-07) |

Para el admin: `python manage.py createsuperuser`.

---

## Prueba rápida del flujo completo

```bash
# 1. Token (las credenciales las imprime sembrar_demo)
curl -X POST http://localhost:8000/api/v1/cuentas/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "laura@correo.com", "password": "casalista2026"}'

# 2. Buscar profesionales que cubran una zona
curl "http://localhost:8000/api/v1/catalogo/profesionales/?zona=Laureles"

# 3. Ver franjas libres
curl "http://localhost:8000/api/v1/reservas/disponibilidad/?profesional_id=1"

# 4. Reservar (dispara Builder + 2 Factories)
curl -X POST http://localhost:8000/api/v1/reservas/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"bloque_id": 2, "direccion": "Calle 33 #70-21", "zona": "Laureles",
       "servicios": [{"servicio_id": 1, "cantidad": 1}]}'

# 5. Pagar (dispara la Factory de pasarelas y confirma la reserva)
curl -X POST http://localhost:8000/api/v1/pagos/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"reserva_id": 1, "medio": "TARJETA"}'
```

---

## Cambiar el comportamiento sin tocar código

Las tres Factories leen su implementación del entorno:

| Variable | Valores | Efecto |
|---|---|---|
| `NOTIFICADOR_TYPE` | `MOCK` / `REAL` | log en consola / correo real |
| `TARIFA_TYPE` | `BASE` / `DINAMICA` | suma simple / recargo nocturno y fin de semana |
| `PASARELA_PAGO_TYPE` | `SIMULADA` / `TARJETA` / `PSE` | aprueba siempre / adaptador real |

```bash
# La misma reserva, con recargo nocturno y de fin de semana:
TARIFA_TYPE=DINAMICA python manage.py sembrar_demo --reiniciar
```

En PowerShell: `$env:TARIFA_TYPE="DINAMICA"; python manage.py sembrar_demo --reiniciar`

---

## Estructura

```
config/            configuración y tabla de rutas raíz
apps/
  comun/           núcleo compartido (dinero, errores, factory base)
  cuentas/         Usuario, Cliente, Profesional
  catalogo/        Servicio
  reservas/        BloqueDisponibilidad, Reserva, DetalleReserva  ← Builder
  pagos/           Pago                                           ← Factory de pasarelas
docs/wiki/         documentación técnica
```

Cada app tiene la misma estructura interna por capas:

```
models.py          solo datos y restricciones de integridad
dominio/           reglas de negocio, puertos, Builder
services.py        Service Layer: una clase por flujo de negocio
infraestructura/   adaptadores y Factories
api/               serializers, APIViews y rutas
tests/
```

La justificación de esta estructura está en
[Estructura del Proyecto](docs/wiki/02-Estructura-del-Proyecto.md).
