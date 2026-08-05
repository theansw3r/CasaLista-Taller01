# CasaLista — Taller 01: Refactorización Arquitectónica

Marketplace de reserva de servicios profesionales para el hogar.
Este repositorio contiene la refactorización del flujo crítico **Crear Reserva**
desde una vista monolítica hacia Arquitectura Limpia con **Service Layer**,
**Builder** y **Factory**.

> 📖 La explicación completa, con diagramas y justificación de las decisiones,
> está en la wiki: **[Implementación del Patrón Creacional](../../wiki/Implementación-del-Patrón-Creacional)**
> (copia versionada en [`docs/wiki/`](docs/wiki/)).

---

## El resultado en una tabla

| | Antes (commit `552cb77`) | Después |
|---|---|---|
| Vista | función de **116 líneas** | CBV de **12 líneas** |
| Reglas de negocio | 13 `if` en la vista | `ReservaBuilder.build()` |
| Notificación | `send_mail()` incrustado | `NotificadorFactory` (MOCK / REAL) |
| Cálculo de tarifa | `if hour >= 19` en la vista | `CalculadorTarifaFactory` (BASE / DINÁMICA) |
| Transaccionalidad | ninguna | `atomic()` + `select_for_update()` |
| Pruebas | 0 | 39 |

---

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py test reservas   # 39 pruebas
python manage.py sembrar_demo    # escenario de demostración
```

## Demostración del Patrón Factory

El mismo código produce dos comportamientos según el entorno:

```bash
# Windows (PowerShell)
$env:NOTIFICADOR_TYPE="MOCK"; $env:TARIFA_TYPE="BASE";     python manage.py sembrar_demo
$env:NOTIFICADOR_TYPE="REAL"; $env:TARIFA_TYPE="DINAMICA"; python manage.py sembrar_demo
```

```bash
# Linux / Mac
NOTIFICADOR_TYPE=MOCK TARIFA_TYPE=BASE     python manage.py sembrar_demo
NOTIFICADOR_TYPE=REAL TARIFA_TYPE=DINAMICA python manage.py sembrar_demo
```

| Variable | Valores | Efecto |
|---|---|---|
| `NOTIFICADOR_TYPE` | `MOCK` \| `REAL` | `NotificadorConsola` \| `NotificadorEmail` |
| `TARIFA_TYPE` | `BASE` \| `DINAMICA` | suma simple \| +20 % nocturno, +15 % fin de semana |

Ver [`.env.example`](.env.example) para el resto de variables.

## El endpoint

```http
POST /api/reservas/
Content-Type: application/json

{
  "bloque_id": 1,
  "direccion": "Calle 30 #45-12",
  "zona": "Laureles",
  "servicios": [{"servicio_id": 1, "cantidad": 1}]
}
```

| Respuesta | Cuándo |
|---|---|
| `201` | Reserva creada en estado `PENDIENTE` |
| `400` | Los datos no tienen la forma esperada |
| `403` | La cuenta autenticada no tiene perfil de cliente |
| `404` | El bloque o el servicio no existen |
| `409` | Se violó una regla de negocio (`RN-01`, `RN-02`, `RN-07`, `RN-08`) |
| `422` | Validación estructural (cantidad ≤ 0, servicio inactivo, …) |

Ejemplo de error:

```json
{"codigo": "RN-07", "error": "El profesional Pedro Osorio no cubre la zona Sabaneta."}
```

---

## Estructura

```
config/                            configuración Django
reservas/
├── views.py                       Capa de Interfaz — CBV de 12 líneas
├── forms.py  dto.py  presenters.py
├── services.py                    Capa de Aplicación — ReservaService
├── models.py                      entidades
├── domain/                        Capa de Dominio
│   ├── reserva_builder.py         ★ PATRÓN BUILDER
│   ├── puertos.py                 interfaces (Inversión de Dependencias)
│   ├── tarifas.py                 estrategias BASE / DINÁMICA
│   └── excepciones.py             errores de negocio con código y estado HTTP
├── infra/                         Capa de Infraestructura
│   ├── factories.py               ★ PATRÓN FACTORY
│   └── notificaciones.py          adaptadores MOCK / REAL
├── management/commands/sembrar_demo.py
└── tests/                         39 pruebas
docs/
├── wiki/                          copia versionada de la wiki
└── CasaLista_Actividad1_Business_Case_y_Dominio.docx
```

---

## Recorrido del código, en orden

1. [`reservas/views.py`](reservas/views.py) — la vista, para ver lo que **ya no** hace.
2. [`reservas/services.py`](reservas/services.py) — el algoritmo del caso de uso.
3. [`reservas/domain/reserva_builder.py`](reservas/domain/reserva_builder.py) — el Builder y sus invariantes.
4. [`reservas/infra/factories.py`](reservas/infra/factories.py) — las Factories.
5. `git show 552cb77:reservas/views.py` — cómo era antes.
