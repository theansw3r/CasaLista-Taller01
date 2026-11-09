# Auditoría previa a cambios - 9 noviembre 2026

Repositorio exclusivo: https://github.com/theansw3r/CasaLista-Taller01.
Referencia: main `d359099b0f7894215c7dfda4f10534088083a624`.
Rama de trabajo: `entrega2/auditoria-integraciones`. No se modifica main durante la implementación.

Se leyó completo Entregable_2.pdf (2 páginas), el código y el historial de main,
las páginas Taller-1, Taller-2 y entrgable-1 de la Wiki.

| Rúbrica | Estado encontrado antes de cambios |
|---|---|
| Correcciones E1 (10%) | Hay paginación, núcleo por capas, Builder/Factories y restricciones del catálogo. El usuario aclara que no hubo correcciones funcionales: el profesor solicitó invertir más en la presentación del front. Pendiente implementar y verificar esa mejora. |
| Arquitectura (10%) | Wiki contiene diagramas Django/Flask/Nginx/Postgres, sin broker ni AWS verificable. |
| Servicios (30%) | JSON público de catálogo y profesionales; pagos Flask. Sin consumo de aliado ni API externa real. TARJETA/PSE son simulaciones locales, no adaptadores HTTP reales. |
| Infraestructura (30%) | Compose con Postgres 16 (dos bases), Django 5.2/DRF, Flask/SQLAlchemy, Nginx. Secretos de ejemplo por defecto, hosts fijos. No hay evidencia de EC2/IP elástica actual. |
| Resiliencia/UX (20%) | Pruebas de reglas y pagos, IDs de petición, timeouts Flask-Django. Notificaciones síncronas, sin Redis/Celery; sin catálogos gettext. HTML/JS con interpolación de datos no escapados, formularios sin validación nativa. |

## Hallazgos que condicionan la entrega

- No confundir esta implementación con TEIS-DjangoSOLID.
- La Wiki afirma que Flask no puede acceder a tablas Django, pero ambas bases
  usan el mismo usuario PostgreSQL. La separación actual es lógica, no una
  frontera de permisos. No se cambiarán roles de una instalación existente
  sin inventariar y respaldar datos.
- No migrar ni borrar pagos antiguos: v1 y v2 mantienen almacenes separados.
- El historial registra identidades `jose` y `theansw3r`, con dos correos distintos;
  eso NO demuestra que existan dos integrantes distintos ni commits de todos.
- No están identificados equipo aliado, contrato, autenticación ni URL.
- No se dispone de sesión AWS Academy/instancia/IP elástica verificada.
- El bono >70% requiere inventario y medición de lógica independiente; un
  microservicio de pagos no permite reclamarlo. Primero requisitos obligatorios.

## Validación inicial

La máquina tiene Docker Desktop instalado, pero inicialmente el daemon estaba
apagado. El Python del sistema es 3.9 (incompatible con Django 5.2); se prepara
un entorno separado Python 3.12. No se usan datos de producción en pruebas.
