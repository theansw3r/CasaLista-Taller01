# Estructura de carpetas

```
apps/
  comun/       # cosas que usan todas las apps (errores, dinero, factory base)
  cuentas/     # Usuario, Cliente, Profesional
  catalogo/    # Servicio
  reservas/    # BloqueDisponibilidad, Reserva, DetalleReserva
  pagos/       # Pago
```

Una app de Django por módulo del Business Case (cada uno se explicó por qué
cambia por razones distintas a los demás). `cuentas` y `catalogo` quedaron
separadas aunque el documento las agrupa, porque el catálogo se consulta
muchísimo más que los perfiles de usuario y en algún momento convendría
cachearlo aparte.

Dentro de cada app:

```
models.py        # solo campos, sin lógica
dominio/          # las reglas de negocio (RN-01, RN-02, etc.), el Builder
services.py       # orquesta el caso de uso, una clase por flujo
infraestructura/  # Factories y adaptadores (correo, pasarela de pago)
api/              # serializers + APIView + urls
tests/
```

La idea es que `views.py` no tenga reglas de negocio (el profe lo pide
explícito), así que las reglas se sacaron a `dominio/` y las vistas solo
llaman al servicio correspondiente.

`dominio/` nunca importa nada de `infraestructura/`: el dominio declara una
interfaz (`puertos.py`) y la infraestructura la implementa. Así el Service
depende de la interfaz, no de una clase concreta.
