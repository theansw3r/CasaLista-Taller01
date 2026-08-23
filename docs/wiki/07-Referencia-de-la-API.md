# 07 · Referencia de la API

Base: `http://localhost:8000/api/v1/`
Documentación interactiva: `http://localhost:8000/api/docs/`
Contrato OpenAPI: `http://localhost:8000/api/schema/`

Todos los endpoints están implementados con `APIView` (no ViewSets ni
`generics`), para tener control explícito de qué método HTTP se atiende, qué
serializer valida y qué código de estado sale.

---

## Autenticación

```http
POST /api/v1/cuentas/token/
Content-Type: application/json

{"username": "laura@correo.com", "password": "casalista2026"}
```

```json
{"access": "eyJhbGci...", "refresh": "eyJhbGci..."}
```

El `username` es el correo: al registrarse se usa el correo como nombre de
usuario. Después, en cada petición privada:

```http
Authorization: Bearer eyJhbGci...
```

---

## Tabla de endpoints

| Método | Ruta | Auth | Códigos |
|---|---|---|---|
| `POST` | `/cuentas/registro/cliente/` | — | 201, 400 |
| `POST` | `/cuentas/registro/profesional/` | — | 201, 400 |
| `POST` | `/cuentas/token/` | — | 200, 401 |
| `POST` | `/cuentas/token/refrescar/` | — | 200, 401 |
| `GET` | `/cuentas/perfil/` | JWT | 200, 401 |
| `GET` | `/catalogo/profesionales/` | — | 200, 400 |
| `GET` | `/catalogo/profesionales/{id}/servicios/` | — | 200, 404 |
| `GET` | `/reservas/disponibilidad/` | — | 200, 400 |
| `POST` | `/reservas/disponibilidad/` | JWT | 201, 400, 404, 409 |
| `GET` | `/reservas/` | JWT | 200, 401 |
| `POST` | `/reservas/` | JWT | **201, 400, 404, 409** |
| `GET` | `/reservas/{id}/` | JWT | 200, 403, 404 |
| `POST` | `/reservas/{id}/cancelacion/` | JWT | 200, 403, 404, 409 |
| `POST` | `/pagos/` | JWT | 201, 400, 403, 404, 409, 502 |
| `GET` | `/pagos/{id}/` | JWT | 200, 403, 404 |
| `GET` | `/salud/` | — | 200, 503 |

---

## Cuentas

### Registrar un cliente

```http
POST /api/v1/cuentas/registro/cliente/

{
  "correo": "laura@correo.com",
  "contrasena": "casalista2026",
  "nombre": "Laura Gómez",
  "telefono": "3001112233"
}
```

`201 Created`

```json
{
  "id": 1,
  "nombre": "Laura Gómez",
  "correo": "laura@correo.com",
  "telefono": "3001112233",
  "creado_en": "2026-08-23T10:00:00-05:00"
}
```

`400` si el correo ya existe (`CTA-01`) o la contraseña tiene menos de 8
caracteres.

### Registrar un profesional

```http
POST /api/v1/cuentas/registro/profesional/

{
  "correo": "andres@casalista.co",
  "contrasena": "casalista2026",
  "nombre": "Andrés Ruiz - Plomería",
  "documento": "1017123456",
  "zonas_cobertura": ["Laureles", "Belén", "Envigado"]
}
```

`201 Created` con `"verificado": false`. **Por RN-07 no puede recibir reservas
hasta que un administrador lo verifique** desde `/admin/` (hay una acción
masiva "Verificar los profesionales seleccionados").

### Perfil

```http
GET /api/v1/cuentas/perfil/
Authorization: Bearer <token>
```

```json
{
  "usuario_id": 2,
  "correo": "laura@correo.com",
  "cliente": {"id": 1, "nombre": "Laura Gómez", ...},
  "profesional": null
}
```

Los dos roles vienen por separado y cualquiera puede ser `null`. Es
consecuencia de cómo se tradujo la herencia `Usuario` del diagrama
(ver [Modelo de Dominio](01-Modelo-de-Dominio)).

---

## Catálogo

### Buscar profesionales — RN-07

```http
GET /api/v1/catalogo/profesionales/?zona=Laureles&texto=plomer
```

```json
[
  {
    "id": 1,
    "nombre": "Andrés Ruiz - Plomería",
    "verificado": true,
    "zonas": ["Laureles", "Belén", "Envigado"],
    "calificacion_promedio": "0.00"
  }
]
```

Solo devuelve profesionales **verificados** cuya cobertura incluye la zona. La
comparación ignora mayúsculas y espacios. Ambos parámetros son opcionales.

### Catálogo de un profesional

```http
GET /api/v1/catalogo/profesionales/1/servicios/
```

```json
[
  {
    "id": 1,
    "nombre": "Reparación de fuga en cocina",
    "descripcion": "",
    "precio_base": "85000.00",
    "duracion_minutos": 60,
    "requiere_visita_previa": false,
    "activo": true,
    "profesional_id": 1,
    "profesional": "Andrés Ruiz - Plomería"
  }
]
```

Omite los servicios dados de baja. `404` (`CAT-02`) si el profesional no existe
o no está verificado.

---

## Agenda

### Consultar franjas libres (público)

```http
GET /api/v1/reservas/disponibilidad/?profesional_id=1&desde=2026-08-24T00:00:00-05:00
```

```json
[
  {
    "id": 2,
    "profesional": "Andrés Ruiz - Plomería",
    "inicio": "2026-08-24T09:00:00-05:00",
    "fin": "2026-08-24T11:00:00-05:00",
    "duracion_minutos": 120,
    "estado": "LIBRE"
  }
]
```

Solo franjas `LIBRE` y futuras: mostrar un horario de ayer solo produciría un
409 después.

### Publicar una franja (profesional)

```http
POST /api/v1/reservas/disponibilidad/
Authorization: Bearer <token del profesional>

{"inicio": "2026-08-24T09:00:00-05:00", "fin": "2026-08-24T11:00:00-05:00"}
```

| Código | Cuándo |
|---|---|
| `201` | franja publicada |
| `400` | `AGD-01` — la franja termina antes de empezar |
| `404` | `CTA-03` — la cuenta no tiene perfil de profesional |
| `409` | `AGD-03` — se solapa con otra franja ya publicada |

De 10 a 11 y de 11 a 12 **no** se consideran solapadas: son consecutivas.

---

## Reservas

### Crear — el flujo más complejo

```http
POST /api/v1/reservas/
Authorization: Bearer <token del cliente>

{
  "bloque_id": 2,
  "direccion": "Calle 33 #70-21, apto 402",
  "zona": "Laureles",
  "servicios": [
    {"servicio_id": 1, "cantidad": 1},
    {"servicio_id": 2, "cantidad": 1}
  ]
}
```

`201 Created`

```json
{
  "id": 1,
  "estado": "PENDIENTE",
  "cliente": "Laura Gómez",
  "profesional": "Andrés Ruiz - Plomería",
  "direccion": "Calle 33 #70-21, apto 402",
  "zona": "Laureles",
  "inicio": "2026-08-24T09:00:00-05:00",
  "fin": "2026-08-24T11:00:00-05:00",
  "total": "140000.00",
  "tarifa_aplicada": "BASE",
  "penalizacion": "0.00",
  "detalles": [
    {
      "servicio": "Reparación de fuga en cocina",
      "cantidad": 1,
      "precio_unitario": "85000.00",
      "duracion_unitaria_minutos": 60,
      "subtotal": "85000.00"
    },
    {
      "servicio": "Cambio de sifón de lavamanos",
      "cantidad": 1,
      "precio_unitario": "55000.00",
      "duracion_unitaria_minutos": 45,
      "subtotal": "55000.00"
    }
  ],
  "creada_en": "2026-08-23T10:05:00-05:00"
}
```

El profesional **no se manda**: se deriva de los servicios, porque RN-02 exige
que todos sean del mismo.

#### Errores posibles

| Código | `codigo` | Cuándo |
|---|---|---|
| `400` | `HTTP-400` | falta un campo, lista de servicios vacía, cantidad ≤ 0 |
| `404` | `AGD-02` | la franja no existe |
| `404` | `CAT-01` | un servicio no existe |
| `404` | `CTA-02` | la cuenta no tiene perfil de cliente |
| `409` | `RN-01` | la franja ya está tomada |
| `409` | `RN-01` | la franja es de otro profesional |
| `409` | `RN-01b` | los servicios no caben en la franja |
| `409` | `RN-02` | los servicios son de dos profesionales distintos |
| `409` | `RN-07` | el profesional no está verificado o no cubre la zona |
| `409` | `CAT-03` | un servicio está dado de baja |

Ejemplo de un 409 con contexto útil:

```json
{
  "error": {
    "codigo": "RN-07",
    "mensaje": "El profesional Andrés Ruiz - Plomería no cubre la zona 'Sabaneta'.",
    "contexto": {
      "zona_solicitada": "Sabaneta",
      "zonas_cubiertas": ["Laureles", "Belén", "Envigado"]
    }
  }
}
```

### Listar y consultar

```http
GET /api/v1/reservas/           # solo las del cliente autenticado
GET /api/v1/reservas/1/         # 403 si es de otro cliente, 404 si no existe
```

### Cancelar — RN-01 + RN-04

```http
POST /api/v1/reservas/1/cancelacion/
{"motivo": "Ya no necesito el servicio"}
```

Se modela como un recurso hijo y no como `DELETE` porque cancelar **no borra**:
cambia el estado, calcula una penalización y libera la franja. El negocio
necesita conservar la reserva para la liquidación.

La penalización sigue RN-04:

| Anticipación | Se retiene |
|---|---|
| más de 24 h | 0 % |
| entre 24 h y 2 h | 30 % |
| menos de 2 h | 100 % |

```json
{"id": 1, "estado": "CANCELADA", "total": "140000.00", "penalizacion": "42000.00", ...}
```

`409` (`RES-05`) si la reserva ya estaba cancelada o completada.

---

## Pagos

### Pagar una reserva — RN-03

```http
POST /api/v1/pagos/
Authorization: Bearer <token del cliente>

{"reserva_id": 1, "medio": "TARJETA"}
```

`medio`: `TARJETA` o `PSE`.

`201 Created`

```json
{
  "id": 1,
  "reserva_id": 1,
  "estado_reserva": "CONFIRMADA",
  "monto": "140000.00",
  "medio": "TARJETA",
  "estado": "APROBADO",
  "pasarela": "SIMULADA",
  "referencia_externa": "SIM-93ba3fd7af5c",
  "creado_en": "2026-08-23T10:06:00-05:00"
}
```

Un pago aprobado deja la reserva en `CONFIRMADA` en la misma transacción. Eso
es RN-03.

| Código | `codigo` | Cuándo |
|---|---|---|
| `400` | `HTTP-400` | el medio de pago no existe |
| `403` | `VAL-403` | la reserva es de otro cliente |
| `404` | `RES-04` | la reserva no existe |
| `409` | `PAG-02` | la reserva ya tiene un pago registrado |
| `409` | `PAG-03` | la reserva no está en estado `PENDIENTE` |
| `409` | `PAG-04` | la pasarela rechazó el pago |
| `502` | `PAG-05` | la pasarela no respondió |

**`PAG-04` es 409 y no 502 a propósito**: la pasarela contestó correctamente,
lo que pasa es que la respuesta fue "no". Reintentar daría lo mismo. Un 502
diría que el sistema falló, y no falló.

Un rechazo **sí** se guarda en la base de datos, con su motivo: un pago
rechazado es información de negocio, no un no-evento.

---

## Operación

### Salud

```http
GET /api/v1/salud/
```

```json
{
  "servicio": "casalista-api",
  "version": "1.0.0",
  "base_de_datos": "ok",
  "id_peticion": "a3f9c2b1..."
}
```

Sin autenticación y sin límite de tasa. Devuelve `503` si la base de datos no
responde, para que el balanceador saque la instancia del pool.

---

## Formato de errores

Todos los errores de la API tienen la misma estructura, vengan del dominio o
de un serializer de DRF:

```json
{
  "error": {
    "codigo": "RN-01",
    "mensaje": "La franja horaria ya fue tomada.",
    "contexto": {"bloque_id": 7}
  }
}
```

`contexto` es opcional. En los errores de validación de campos trae el detalle:

```json
{
  "error": {
    "codigo": "HTTP-400",
    "mensaje": "La peticion tiene campos invalidos.",
    "contexto": {"campos": {"direccion": ["Este campo es requerido."]}}
  }
}
```

### Prefijos de los códigos

| Prefijo | Módulo |
|---|---|
| `RN-xx` | reglas del Business Case (RN-01, RN-02, RN-07…) |
| `CTA-xx` | Cuentas |
| `CAT-xx` | Catálogo |
| `AGD-xx` | Agenda |
| `RES-xx` | Reservas |
| `PAG-xx` | Pagos |
| `VAL-xxx` | validaciones transversales (403, 404) |
| `HTTP-xxx` | errores generados por DRF |

Los códigos `RN-` son los mismos de la tabla del Business Case, para poder
rastrear un error de producción hasta el documento de negocio.

---

## Cabeceras

| Cabecera | Dirección | Para qué |
|---|---|---|
| `Authorization: Bearer <jwt>` | entrada | autenticación sin estado |
| `X-Request-ID` | entrada y salida | correlación de logs entre el Gateway y la aplicación |

Si `X-Request-ID` no llega, la aplicación genera uno y lo devuelve igual.
