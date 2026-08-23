# 05 · Diagrama de Secuencia

La funcionalidad más compleja implementada es **crear una reserva**:
`POST /api/v1/reservas/`.

Es la que atraviesa las cinco capas, dispara el Builder y las dos Factories del
módulo de reservas, valida siete reglas de negocio y abre una transacción con
bloqueo de fila. También es donde se ve, en un solo recorrido, por qué la
arquitectura está montada así.

---

## Camino feliz

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant GW as API Gateway
    participant V as ReservasView<br/>(APIView)
    participant SER as CrearReservaSerializer
    participant SVC as ReservaService
    participant NF as NotificadorFactory
    participant TF as CalculadorTarifaFactory
    participant B as ReservaBuilder
    participant RA as ReglasAgenda
    participant PC as PoliticaDeCobertura
    participant DB as Base de datos
    participant N as Notificador

    Cliente->>GW: POST /api/v1/reservas/<br/>Bearer JWT
    GW->>GW: valida el JWT y el límite de tasa
    GW->>V: reenvía + X-Request-ID

    Note over V,SER: 1 · Validación de FORMA
    V->>SER: CrearReservaSerializer(data=request.data)
    SER-->>V: válido
    V->>SER: a_comando(usuario_id)
    SER-->>V: CrearReservaCommand (dataclass inmutable)

    Note over SVC,TF: 2 · El servicio resuelve sus colaboradores
    V->>SVC: crear_reserva(comando)
    SVC->>NF: crear()
    NF-->>SVC: NotificadorConsola
    SVC->>TF: crear()
    TF-->>SVC: TarifaBase

    Note over SVC,DB: 3 · Ids → entidades
    SVC->>DB: Cliente por usuario_id
    DB-->>SVC: Cliente
    SVC->>DB: BloqueDisponibilidad por id
    DB-->>SVC: Bloque
    SVC->>DB: Servicio por cada línea
    DB-->>SVC: Servicios

    Note over SVC,B: 4 · Se arma el Builder (nada se valida todavía)
    SVC->>B: para_cliente / en_bloque / en_direccion
    SVC->>B: con_calculador_tarifa(TarifaBase)
    loop por cada línea del comando
        SVC->>B: agregar_servicio(servicio, cantidad)
    end

    Note over B,PC: 5 · build(): valida TODO antes de escribir
    SVC->>B: build()
    B->>B: datos mínimos, líneas y cantidades
    B->>PC: exigir_habilitado(profesional, zona) · RN-07
    PC-->>B: ok
    B->>B: mismo profesional · RN-02
    B->>RA: exigir_disponible(bloque) · RN-01
    RA->>DB: ¿hay reserva activa en el bloque?
    DB-->>RA: no
    RA-->>B: ok
    B->>RA: duracion_minutos(bloque)
    RA-->>B: 120 ≥ 60 solicitados

    Note over B,DB: 6 · Transacción con bloqueo
    B->>DB: BEGIN
    B->>DB: SELECT ... FOR UPDATE del bloque
    DB-->>B: Bloque (fila bloqueada)
    B->>RA: exigir_disponible(bloque) · segunda vez
    RA-->>B: ok
    B->>B: total = TarifaBase.calcular(detalles, bloque)
    B->>DB: INSERT Reserva (PENDIENTE)
    B->>DB: bulk_create DetalleReserva<br/>precio y duración congelados
    B->>DB: UPDATE bloque → OCUPADO
    B->>DB: COMMIT
    B-->>SVC: Reserva

    Note over SVC,N: 7 · Notificación, YA FUERA de la transacción
    SVC->>N: enviar_confirmacion_reserva(reserva)
    N-->>SVC: (no lanza nunca)
    SVC-->>V: Reserva

    V->>V: ReservaSerializer(reserva).data
    V-->>GW: 201 Created
    GW-->>Cliente: 201 + X-Request-ID
```

### Los cuatro momentos que importan

**Paso 1 — la forma se valida antes de tocar nada.**
Un cuerpo mal armado se rechaza con 400 sin abrir una sola conexión a la base
de datos ni ejecutar una sola regla.

**Paso 4 — armar el Builder no valida nada.**
El bucle `agregar_servicio` puede correr en cualquier orden. Si validara sobre
la marcha, no podría decir *qué* profesionales estaban en conflicto: solo que
el segundo no coincidía con el primero.

**Paso 6 — la validación ocurre dos veces, y es a propósito.**
La primera (paso 5) es optimista y barata: rechaza casi todo sin bloquear
nada. La segunda ocurre con la fila del bloque bloqueada. Entre las dos hay
una ventana en la que otro cliente pudo tomar la misma franja, y esa ventana
es exactamente lo que el bloqueo cierra.

**Paso 7 — la notificación queda fuera de la transacción.**
Por dos razones: una llamada de red lenta mantendría el bloqueo abierto más
tiempo del necesario, y una notificación caída no puede tumbar una reserva ya
guardada.

---

## Caminos de error

Todos terminan igual: el dominio lanza su excepción, **nadie la captura en el
camino**, y el manejador central la traduce.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant V as ReservasView
    participant SER as Serializer
    participant SVC as ReservaService
    participant B as ReservaBuilder
    participant H as manejar_excepcion
    participant DB as Base de datos

    alt 400 · la forma es inválida
        Cliente->>V: POST sin "direccion"
        V->>SER: is_valid(raise_exception=True)
        SER--xV: ValidationError
        V--xH: (sin try/except)
        H-->>Cliente: 400 {"error": {"codigo": "HTTP-400", "contexto": {"campos": {...}}}}

    else 404 · el recurso no existe
        Cliente->>V: POST bloque_id=999999
        V->>SVC: crear_reserva(comando)
        SVC->>DB: BloqueDisponibilidad.get(pk=999999)
        DB--xSVC: DoesNotExist
        SVC--xH: BloqueNoEncontrado (estado_http = 404)
        H-->>Cliente: 404 {"error": {"codigo": "AGD-02", ...}}

    else 409 · choca con el estado del sistema
        Cliente->>V: POST sobre una franja ya tomada
        V->>SVC: crear_reserva(comando)
        SVC->>B: build()
        B->>DB: ¿hay reserva activa en el bloque?
        DB-->>B: sí
        B--xH: BloqueNoDisponible (estado_http = 409)
        H-->>Cliente: 409 {"error": {"codigo": "RN-01", ...}}

    else 409 · RN-07, el profesional no cubre la zona
        Cliente->>V: POST zona="Sabaneta"
        V->>SVC: crear_reserva(comando)
        SVC->>B: build()
        B--xH: ProfesionalNoHabilitado
        H-->>Cliente: 409 {"error": {"codigo": "RN-07",<br/>"contexto": {"zonas_cubiertas": ["Laureles", "Belen"]}}}
    end
```

La flecha `V--xH` es la clave del diseño: **la excepción no pasa por la
vista**. DRF la intercepta y llama al manejador configurado en `settings.py`.
Por eso `views.py` no tiene un solo `try/except` y aun así cada error sale con
su código correcto.

Las cuatro ramas están probadas en `apps/reservas/tests/test_api.py`.

---

## El flujo completo del negocio

Crear la reserva es el paso 2 de cinco. Así se ve el ciclo entero de la
sección 1.5 del Business Case, con lo implementado y lo pendiente:

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant CAT as CatalogoService
    participant RES as ReservaService
    participant PAG as PagoService
    participant CV as CicloDeVidaReserva
    participant PSL as PasarelaPagoFactory

    Note over C,CAT: 1 · Buscar (RN-07)
    C->>CAT: GET /catalogo/profesionales/?zona=Laureles
    CAT-->>C: solo verificados que cubren la zona

    Note over C,RES: 2 · Reservar
    C->>RES: POST /reservas/
    RES-->>C: 201 · Reserva PENDIENTE

    Note over C,CV: 3 · Pagar (RN-03)
    C->>PAG: POST /pagos/ {reserva_id, medio}
    PAG->>PSL: para_medio("TARJETA")
    PSL-->>PAG: PasarelaTarjeta
    PAG->>PAG: cobrar(total)
    PAG->>CV: confirmar(reserva)
    CV-->>PAG: estado = CONFIRMADA
    PAG-->>C: 201 · Pago APROBADO

    Note over C,CV: 4 · Ejecutar la visita — Entrega 2
    Note over C,CV: 5 · Liquidar (RN-06) — Entrega 2

    Note over C,RES: Alterno · Cancelar (RN-01 + RN-04)
    C->>RES: POST /reservas/{id}/cancelacion/
    RES->>CV: cancelar(reserva)
    RES->>RES: penalización según la ventana de tiempo
    RES->>RES: libera el bloque
    RES-->>C: 200 · Reserva CANCELADA
```

---

## Estados de la reserva

La máquina de estados vive en `apps/reservas/dominio/ciclo_de_vida.py`,
declarada como un diccionario y no repartida en condicionales:

```python
TRANSICIONES_PERMITIDAS = {
    Estado.PENDIENTE:  {Estado.CONFIRMADA, Estado.CANCELADA},
    Estado.CONFIRMADA: {Estado.COMPLETADA, Estado.CANCELADA},
    Estado.COMPLETADA: set(),
    Estado.CANCELADA:  set(),
}
```

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE : ReservaBuilder.build()
    PENDIENTE --> CONFIRMADA : pago aprobado · RN-03
    PENDIENTE --> CANCELADA : cancelación · RN-04
    CONFIRMADA --> COMPLETADA : visita ejecutada <i>(Entrega 2)</i>
    CONFIRMADA --> CANCELADA : cancelación · RN-04
    COMPLETADA --> [*]
    CANCELADA --> [*]

    note right of CANCELADA
        Libera el bloque (RN-01)
        y calcula la penalización
    end note
```

Cualquier transición fuera de ese grafo levanta
`TransicionDeEstadoInvalida` → **409**. Por ejemplo, cancelar dos veces:

```python
def test_409_al_cancelar_dos_veces(self):
    self.client.post(url, {}, format="json")
    respuesta = self.client.post(url, {}, format="json")

    self.assertEqual(respuesta.status_code, 409)
    self.assertEqual(respuesta.data["error"]["codigo"], "RES-05")
```
