# Guion breve para la sustentación

## 1. Funcionalidad seleccionada

Seleccionamos **Crear Reserva** porque es el centro transaccional de CasaLista. Antes de guardar, debemos comprobar la disponibilidad del bloque, que los servicios pertenezcan al mismo profesional, calcular el total y ocupar la agenda.

## 2. Problema arquitectónico

Si esas reglas se dejan en la vista, la capa web termina con muchos condicionales, consultas y operaciones de persistencia. Eso dificulta las pruebas y aumenta el acoplamiento con Django.

## 3. Refactorización

La vista ahora solo recibe el request y llama a `ReservaService`.

El servicio controla la transacción, bloquea el horario, consulta los servicios, invoca el Builder, guarda el resultado y solicita la notificación.

`ReservaBuilder` construye la reserva paso a paso y no entrega el objeto hasta que todas las reglas se cumplen.

`NotificadorFactory` selecciona entre consola y correo mediante `NOTIFICATION_BACKEND`, por lo que el comportamiento cambia sin tocar el caso de uso.

## 4. SOLID

Aplicamos responsabilidad única porque cada clase tiene una función específica. También aplicamos inversión de dependencias: el servicio recibe un notificador por contrato, lo que permite inyectar un doble de prueba.

## 5. Resultado

La vista tiene menos de quince líneas, la lógica queda centralizada y probada, y el sistema está preparado para cambiar la infraestructura de notificaciones sin afectar el dominio.
