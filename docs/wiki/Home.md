# CasaLista — Wiki Técnica

Marketplace de reserva de servicios profesionales para el hogar en el Área
Metropolitana del Valle de Aburrá.

**Entrega No. 1 — Núcleo de Negocio y Exposición de API Profesional**
Arquitectura de Software 2026 · Prof. Nicolás Ramírez Vélez

---

## Contenido

| Página | Qué responde |
|---|---|
| [01 · Modelo de Dominio](01-Modelo-de-Dominio) | Qué clases del diagrama se implementaron y cuáles quedan para la Entrega 2 |
| [02 · Estructura del Proyecto](02-Estructura-del-Proyecto) | Por qué las carpetas están organizadas así y no de otra forma |
| [03 · Arquitectura por Capas](03-Arquitectura-por-Capas) | Cómo se aplica el Service Layer y dónde se ve cada principio SOLID |
| [04 · Patrones Creacionales](04-Patrones-Creacionales) | Builder y Factory: por qué ahí, cómo funcionan, qué problema resolvieron |
| [05 · Diagrama de Secuencia](05-Diagrama-de-Secuencia) | El flujo más complejo del sistema, paso a paso |
| [06 · API Gateway](06-API-Gateway) | Cómo está preparado el sistema para escalar detrás de un Gateway |
| [07 · Referencia de la API](07-Referencia-de-la-API) | Endpoints, cuerpos y códigos de estado |

---

## Resumen de la entrega

CasaLista viene del Taller 01, donde el flujo *Crear Reserva* se refactorizó
para sacar la lógica de la vista. Esta entrega **rehace la arquitectura
completa** sobre esa base:

| | Taller 01 | Entrega 1 |
|---|---|---|
| Clases de dominio | 7 de 10 | **8 de 10** (se agrega `Pago`) |
| Presentación | vistas web con formularios Django | **Django REST Framework** con `APIView` y serializers |
| Estructura | 2 apps (`cuentas`, `reservas`) | **4 apps + núcleo compartido**, una por módulo del dominio |
| Comportamiento en los modelos | sí (`calcular_total`, `cubre_zona`, `esta_libre`) | **no**: los modelos solo persisten |
| Patrones creacionales | 1 Builder, 2 Factories | 1 Builder, **3 Factories** |
| Manejo de errores | `try/except` en cada vista | **manejador central**, cero `try/except` en las vistas |
| Autenticación | sesión de Django | **JWT sin estado** (validable por el Gateway) |
| Contrato | ninguno | **OpenAPI** publicado en `/api/schema/` |
| Pruebas | 6 archivos | **128 pruebas** |

### El cambio más importante

El enunciado advierte que cualquier cálculo o validación dentro de un método
de un modelo penaliza SOLID. En el Taller 01 los modelos tenían
comportamiento de dominio, siguiendo la idea de "modelo rico". En esta entrega
esa decisión se revirtió: **los modelos son mapas de datos y nada más**, y
cada método del diagrama de clases se implementó en la clase de dominio que le
corresponde.

La tabla completa de esa migración está en
[01 · Modelo de Dominio](01-Modelo-de-Dominio#dónde-quedó-cada-método-del-diagrama).

---

## Reglas de negocio del Business Case

Estas son las reglas que el código implementa. Cada una tiene un código que
aparece en las excepciones del dominio y en las respuestas de error de la API,
para poder rastrear un error de producción hasta el documento de negocio.

| Código | Regla | Dónde se aplica | Estado |
|---|---|---|---|
| RN-01 | Un bloque solo puede tener una reserva activa; al cancelar se libera | `dominio/agenda.py`, `services.py` | Implementada |
| RN-02 | Todos los servicios de una reserva son del mismo profesional | `dominio/reserva_builder.py` | Implementada |
| RN-03 | Una reserva solo se confirma si hay un pago aprobado | `apps/pagos/services.py` | Implementada |
| RN-04 | Penalización por cancelación: 0 % / 30 % / 100 % | `dominio/cancelacion.py` | Implementada |
| RN-05 | Solo el cliente de una reserva completada puede reseñar | — | Entrega 2 (`Reseña`) |
| RN-06 | La comisión se calcula al completar, no al reservar | — | Entrega 2 (`Liquidación`) |
| RN-07 | Solo aparecen profesionales verificados que cubran la zona | `apps/cuentas/dominio/cobertura.py` | Implementada |

5 de 7 reglas implementadas. Las dos pendientes dependen de las dos clases
que quedaron fuera del alcance.
