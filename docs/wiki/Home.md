# CasaLista — Wiki técnica

**CasaLista** es un marketplace de reserva de servicios profesionales para el
hogar en el Área Metropolitana del Valle de Aburrá: oficios técnicos de visita
corta y agendable (plomería, electricidad, reparación de electrodomésticos,
pintura y cerrajería).

## Páginas

- **[[Implementación del Patrón Creacional]]** — Taller 01: refactorización del
  flujo *Crear Reserva* a Service Layer + Builder + Factory.

## Contexto del proyecto

| | |
|---|---|
| Flujo núcleo | reserva → pago → liquidación (sección 1.5 del Business Case) |
| Modelo de ingresos | comisión del 12 % sobre la reserva completada |
| Atributo de calidad #1 | consistencia de la agenda |
| Módulos del dominio | Cuentas y Catálogo · Agenda y Reservas · Pagos y Liquidación · Reputación |

El Business Case completo y el modelo de dominio están en
[`docs/CasaLista_Actividad1_Business_Case_y_Dominio.docx`](../CasaLista_Actividad1_Business_Case_y_Dominio.docx).

## Reglas de negocio

| Código | Regla | ¿Implementada en el Taller 01? |
|---|---|---|
| RN-01 | Un bloque solo puede tener una reserva activa | Sí — `ReservaBuilder` |
| RN-02 | Todos los servicios de una reserva son del mismo profesional | Sí — `ReservaBuilder` |
| RN-03 | Una reserva se confirma solo con un pago aprobado | No — siguiente caso de uso |
| RN-04 | Política de cancelación por anticipación | No |
| RN-05 | Solo el cliente de una reserva COMPLETADA reseña | No |
| RN-06 | La comisión se calcula al completar | No |
| RN-07 | El profesional debe estar verificado y cubrir la zona | Sí — `ReservaBuilder` |
| RN-08 | *(derivada)* Los servicios caben en la franja reservada | Sí — `ReservaBuilder` |
