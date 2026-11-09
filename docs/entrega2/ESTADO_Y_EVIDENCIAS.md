# Estado de Entrega 2 - 9 noviembre 2026

## Alcance y corrección de Entrega 1

Se trabaja exclusivamente en CasaLista-Taller01, rama de trabajo
`entrega2/auditoria-integraciones`, referencia main d359099.
El usuario aclaró que no hubo correcciones funcionales del profesor; solicitó
invertir más en la presentación del front. Se implementó una nueva identidad
visual y se inspeccionaron navegación, login e inglés en navegador, con diseño
móvil de 390 px sin desbordamiento horizontal. No hay acta externa adicional.

| Criterio | Estado verificable |
|---|---|
| Corrección E1 | Mejora visual implementada; observación indicada por el usuario. |
| Arquitectura | Diagramas y decisiones actualizados; AWS marcado como destino pendiente. |
| Servicio propio | Catálogo y profesionales JSON públicos, paginados y sin datos privados. |
| Tercero / Adapter / DIP | Open-Meteo real por adaptador inyectado; visible en interfaz; evidencia HTTP. |
| Aliado | BLOQUEADO: falta identidad, URL, esquema y autenticación. No cumplido. |
| Docker / gateway | Siete servicios levantados y probados localmente; hosts y DNS corregidos tras prueba real. |
| Redis / Celery | Reserva con outbox persistente; worker, scheduler y recuperación ante caída real de Redis. |
| i18n / UX | gettext para templates, JS, dominio y Flask; ES/EN, formularios, escape, navegación y diseño móvil. |
| AWS / EIP | PENDIENTE: el usuario confirma que no hay instancia creada. Sin acceso al lab aún. |
| main / commits | Avance preparado en rama separada con la identidad autorizada de Lucas Saldarriaga. Integración a main pendiente; consultar HEAD y el remoto para el SHA publicado. |
| Bono >70% | No reclamado. Prioridad de obligatorios. |

## Evidencias ejecutadas

- `evidencias/http-local.json`: 13 comprobaciones por Nginx, incluyendo JSON
  propio, proveedor externo real, bloqueo interno, autenticación, reserva 201,
  pago Flask 201 y rechazo de segundo pago 409. El pago es SIMULADO.
- `evidencias/resiliencia-local.json`: Redis detenido, reserva 201 en 6.24 s,
  evento persistido sin entregar, recuperación posterior; Flask detenido produce
  503 mientras Django sigue 200, y Flask vuelve a 200.
- Suites: 167 pruebas Django y 30 Flask pasan; migraciones consistentes,
  catálogos completos y configuración Nginx/Compose válida.
- Revisión visual en navegador: portada ES, cambio EN, login cliente,
  reservas EN y viewport 390x844 sin overflow. También se publicó un horario
  desde el panel profesional y se creó/pagó la reserva #5 desde el navegador
  en inglés; quedó CONFIRMADA con pasarela SIMULADA. Registro:
  `evidencias/navegador-local.json`. Los textos de contenido de usuarios
  (por ejemplo descripciones de demo en español) no se traducen automáticamente.
- Celery entregó los eventos al backend consola. No se ha demostrado un envío
  a SMTP externo ni recepción por un destinatario.

Estas evidencias son locales. No certifican AWS ni comunicación con un aliado.
Los JSON guardan IDs de demo y de petición; no contienen JWT, .env ni claves.

## Commits reales por integrante

`evidencias/commits-main-original.txt` conserva los 14 commits de main auditados,
con hash, autor, correo, fecha y asunto. Aparecen 9 como `jose` y 5 como
`theansw3r`; dos identidades no prueban dos personas. El documento de negocio
conserva marcadores Integrante 1/2/3 y no permite verificar el equipo real.
El usuario autorizó la identidad Git Lucas Saldarriaga
<llsaldarrq@eafit.edu.co> para registrar este avance asistido. Se configura
solo en este repositorio. Faltan nombres/usuarios de los demás integrantes
y la verificación de sus contribuciones reales. No se modifica la autoría del historial ni se reparten commits
artificialmente para simular participación.

## Condiciones para integrar y entregar

1. Continuar desde la rama publicada `entrega2/auditoria-integraciones` y revisar
   el avance. Seguir la guía `CONTINUAR_TRABAJO.md`.
2. Obtener contrato y acceso del aliado; implementar y probar el consumo real.
3. Crear/verificar EC2 y EIP en el laboratorio autorizado; desplegar el SHA real.
4. Verificar SMTP si se quiere demostrar recepción externa en vez de consola.
5. Registrar contribuciones auténticas de cada integrante, ejecutar validación
   final y actualizar estas evidencias con resultados reales.
6. Integrar a main con revisión de los cambios y conservar los datos del despliegue.
   No se declara la entrega completa mientras falten aliado, AWS y main publicado.
