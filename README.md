# CasaLista — Taller 01: Refactorización Arquitectónica

Implementación de una refactorización sobre la funcionalidad crítica **Crear Reserva** de CasaLista.

La solución aplica:

- Vista Django basada en clase con responsabilidad mínima.
- Service Layer para orquestar el caso de uso.
- `ReservaBuilder` con interfaz fluida para construir una reserva válida.
- `NotificadorFactory` para alternar entre comportamiento `CONSOLE` y `EMAIL` mediante una variable de entorno.
- Inyección de dependencias para facilitar pruebas y sustitución de infraestructura.
- Transacción y bloqueo pesimista para evitar que dos clientes ocupen el mismo bloque.
- Pruebas automáticas de las reglas principales.

## 1. Funcionalidad seleccionada

El flujo seleccionado es **Crear Reserva**, porque concentra varias reglas del negocio:

1. El bloque debe estar libre.
2. El profesional debe estar verificado.
3. Todos los servicios deben pertenecer al mismo profesional.
4. Las cantidades deben ser positivas.
5. El total debe calcularse antes de guardar.
6. La reserva inicia en estado `PENDIENTE`.
7. El bloque queda `OCUPADO`.
8. La notificación se ejecuta únicamente después de confirmar la transacción.

## 2. Estructura

```text
reservas/
├── domain/
│   ├── builders.py
│   └── exceptions.py
├── infra/
│   ├── factories.py
│   └── notifiers.py
├── migrations/
│   └── __init__.py
├── tests/
│   └── test_reserva_service.py
├── apps.py
├── models.py
├── services.py
├── urls.py
└── views.py

wiki/
└── Implementacion-del-Patron-Creacional.md

diagrams/
├── flujo_crear_reserva.mmd
└── clases_refactor.mmd
```

## 3. Integración en un proyecto Django

1. Copie la carpeta `reservas` dentro del proyecto.
2. Agregue `"reservas"` a `INSTALLED_APPS`.
3. Incluya las URL:

```python
# config/urls.py
from django.urls import include, path

urlpatterns = [
    path("api/", include("reservas.urls")),
]
```

4. Genere y aplique las migraciones:

```bash
python manage.py makemigrations reservas
python manage.py migrate
```

5. Configure el backend de notificación:

```env
NOTIFICATION_BACKEND=CONSOLE
```

Valores soportados:

- `CONSOLE`: escribe la confirmación en el log.
- `EMAIL`: usa `django.core.mail.send_mail`.

6. Ejecute las pruebas:

```bash
python manage.py test reservas
```

## 4. Ejemplo de solicitud

El usuario debe estar autenticado.

```http
POST /api/reservas/
Content-Type: application/json

{
  "bloque_id": 10,
  "servicios": [
    {"servicio_id": 3, "cantidad": 1},
    {"servicio_id": 4, "cantidad": 2}
  ]
}
```

Respuesta esperada:

```json
{
  "id": 21,
  "estado": "PENDIENTE",
  "total": "180000.00"
}
```

## 5. Correspondencia con la rúbrica

| Criterio | Evidencia |
|---|---|
| Service Layer y SOLID | `reservas/services.py`; la vista solo interpreta el request y delega. |
| Inyección de dependencias | `ReservaService(notificador=...)` y `service_class` reemplazable en la vista. |
| Factory | `reservas/infra/factories.py`; comportamiento definido por `NOTIFICATION_BACKEND`. |
| Builder | `reservas/domain/builders.py`; interfaz fluida y validación antes de guardar. |
| Wiki | `wiki/Implementacion-del-Patron-Creacional.md`. |
| Git Flow | `git_commits_sugeridos.txt`. |
| Pruebas | `reservas/tests/test_reserva_service.py`. |

## 6. Decisión sobre notificaciones

La actividad anterior de CasaLista dejó las notificaciones fuera del alcance funcional. En este taller se incorpora una notificación mínima únicamente como **dependencia de infraestructura** para evidenciar el patrón Factory solicitado. No se agrega lógica de notificación al modelo de dominio y el caso de uso continúa funcionando con el backend `CONSOLE`.
