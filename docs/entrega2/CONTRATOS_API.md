# Servicios e integración

Base local validada: `http://localhost:8080`. En AWS se reemplazará por la IP
elástica verificada. No hay IP pública de CasaLista disponible todavía.

Todas las rutas siguientes devuelven JSON. Las APIs privadas requieren
`Authorization: Bearer <JWT>`; no se incluyen tokens reales en documentación.
Accept-Language admite `es` y `en`.

## Servicio propio para proveer al equipo aliado

`GET /api/v1/catalogo/profesionales/?zona=Laureles&categoria=PLOMERIA&pagina=1&tamano=20`

Sin autenticación. Devuelve profesionales verificados que cumplen cobertura y
categoría; incluye `total`, `pagina`, `paginas`, `resultados`.
Cada resultado tiene `id`, `nombre`, `descripcion`, `verificado`, `zonas`,
`calificacion_promedio`. No expone correo, teléfono, documentos o credenciales.
Parámetros opcionales; tamaño máximo 100. La lista vacía es 200.

`GET /api/v1/catalogo/profesionales/{id}/servicios/` publica servicios activos
paginados, con `id`, `categoria`, `categoria_nombre`, `nombre`, `descripcion`,
`precio_base` (decimal como string COP), `duracion_minutos`,
`requiere_visita_previa`, `activo`, `profesional_id`, `profesional`.
Un profesional inexistente/no verificado devuelve 404.

Errores de forma/dominio:
```json
{"error":{"codigo":"VAL-000","mensaje":"Mensaje localizado","contexto":{}}}
```
`contexto` es opcional. Los códigos son estables; no comparar textos traducidos.

## Clima externo

`GET /api/v1/integraciones/clima/`

Sin autenticación. Open-Meteo entrega condiciones actuales para Medellín;
respuesta propia: `ciudad`, `temperatura_c`, `precipitacion_mm`, `observado_en`
(fecha/hora local según `zona_horaria`), `zona_horaria`, `fuente`, `atribucion`.
Errores de proveedor o esquema: 503 / `INT-503`. No se generan datos sustitutos.
La interfaz atribuye a [Open-Meteo](https://open-meteo.com/).
Documentación del proveedor: [Forecast API](https://open-meteo.com/en/docs).
Uso académico; revisar términos/licencia si se transforma en un producto comercial.

## Equipo aliado: bloqueo explícito

`GET /api/v1/integraciones/aliado/` devuelve 503 / `ALIADO-PENDIENTE`.
Es un indicador del bloqueo, **no una integración implementada**.
No se ha recibido identidad, URL, autenticación ni esquema del equipo aliado.
No se ha inventado un contrato genérico que se pretenda dar por compatible.

Al recibirlo: acordar datos/caso de uso y permisos; revisar endpoint y ejemplo
real; implementar un puerto y su adaptador; validar timeout, 4xx/5xx, JSON
inválido y vacío; mostrar resultados en la tarjeta del aliado; capturar evidencia
con fecha y URL pública y con cualquier secreto eliminado.

## Pago estrangulado

`POST /api/v2/pagos/` con JWT y `{"reserva_id": 1, "medio": "TARJETA"}`.
201 aprobado y confirmado; 400 cuerpo inválido; 401 sin credenciales; 403 ajeno;
404 reserva/pago inexistente; 409 reserva no pagable o ya tiene pago;
502 `PAG-07` si se aprobó sin lograr confirmar (conciliación manual);
503 `PAG-06` si Django no responde. `GET /api/v2/pagos/{id}/` consulta pago propio.
El resultado de demo identifica `pasarela: SIMULADA` y referencia `SIM-...`.

Las rutas `/interno/*` se bloquean desde Nginx incluso si el cliente presenta
credenciales. Entre servicios, confirmar requiere `X-Token-Servicio`.
