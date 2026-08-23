# Diagrama de secuencia — Crear reserva

Es el flujo más complejo del sistema: `POST /api/v1/reservas/`. Pasa por la
vista, el service, el Builder (que valida todo) y hace la escritura dentro de
una transacción.

```mermaid
sequenceDiagram
    actor Cliente
    participant V as ReservasView
    participant S as ReservaService
    participant B as ReservaBuilder
    participant DB as Base de datos
    participant N as Notificador

    Cliente->>V: POST /reservas/ (JWT)
    V->>V: valida forma con el serializer
    V->>S: crear_reserva(comando)
    S->>DB: busca cliente, bloque, servicios
    S->>B: arma el builder con esos datos
    S->>B: build()

    B->>B: valida RN-02 (mismo profesional)
    B->>B: valida RN-07 (profesional habilitado)
    B->>B: valida RN-01 (bloque libre)
    B->>B: valida que quepa en la duración

    alt alguna regla falla
        B-->>S: excepción de dominio
        S-->>V: la misma excepción sube
        V-->>Cliente: 409 (o 404, según el error)
    else todo válido
        B->>DB: BEGIN
        B->>DB: SELECT bloque FOR UPDATE (evita doble reserva)
        B->>DB: vuelve a chequear que siga libre
        B->>DB: guarda Reserva + DetalleReserva
        B->>DB: marca el bloque como OCUPADO
        B->>DB: COMMIT
        B-->>S: reserva creada
        S->>N: notifica (fuera de la transacción)
        S-->>V: reserva
        V-->>Cliente: 201 + datos de la reserva
    end
```

Dos cosas para explicar en la sustentación si preguntan:

- **El `SELECT FOR UPDATE`** es porque, entre que se valida que el bloque está
  libre y se guarda la reserva, otro cliente podría estar reservando la misma
  franja al mismo tiempo. Se vuelve a chequear ya con el bloqueo puesto.
- **La notificación va fuera de la transacción** para no tener la fila
  bloqueada mientras se manda un correo (que puede demorarse).

El código de esta parte está en `apps/reservas/dominio/reserva_builder.py`.
