# Preparación para API Gateway

Un API Gateway es lo que se pone delante de la API en producción: recibe todo
el tráfico y se encarga de cosas como autenticación, límite de peticiones,
HTTPS y enrutar hacia el servicio correcto. Estas son las decisiones que se
tomaron pensando en eso:

- **Rutas versionadas y por módulo**: todo cuelga de `/api/v1/`, y cada
  módulo tiene su propio prefijo (`/cuentas/`, `/catalogo/`, `/reservas/`,
  `/pagos/`). Un Gateway enruta por prefijo, así que el día que se quiera
  sacar `pagos` a otro servicio, solo hay que cambiar la configuración del
  Gateway, no el código.

- **Autenticación con JWT en vez de sesión**: el JWT no necesita que el
  servidor guarde nada, así que cualquier instancia puede validarlo (o el
  Gateway mismo, sin ni siquiera llegar a la app). Con sesión de Django, el
  cliente tendría que volver siempre al mismo servidor.

- **Contrato OpenAPI publicado** en `/api/schema/` (se genera con
  `drf-spectacular`, no se escribe a mano). Un Gateway puede leer eso e
  importar automáticamente las rutas.

- **Todos los errores tienen la misma forma** (`{"error": {"codigo": ...,
  "mensaje": ...}}`), venga de una regla de negocio o de un dato mal
  mandado. Esto lo maneja un solo lugar
  (`apps/comun/api/manejador_errores.py`), así que las vistas no tienen
  `try/except`.

- **Endpoint de salud** (`GET /api/v1/salud/`) sin autenticación, para que el
  balanceador sepa si la instancia sigue viva.

- **Nada está hardcodeado**: todo lo que puede cambiar entre desarrollo y
  producción (base de datos, si está detrás de un proxy, límites de
  peticiones) se lee de variables de entorno (`.env`).

Lo que **no** se movería nunca al Gateway son las reglas de negocio (RN-01,
RN-07, etc.): esas se quedan en el dominio de la aplicación. El Gateway solo
resuelve cosas de infraestructura.
