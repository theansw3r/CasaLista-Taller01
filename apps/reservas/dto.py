"""
Comandos del modulo Agenda y Reservas.

Son la frontera entre la capa de API y la de aplicacion. El servicio recibe un
`CrearReservaCommand`, nunca un `HttpRequest` ni un serializer: gracias a eso
el mismo caso de uso sirve para la API REST, para el comando `sembrar_demo` y
para una futura cola de tareas sin cambiar una linea.

Son `frozen=True` a proposito: un comando describe una intencion ya tomada.
Si el servicio pudiera modificarlo, el dato que se valido y el que se ejecuta
podrian dejar de ser el mismo.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LineaSolicitada:
    servicio_id: int
    cantidad: int


@dataclass(frozen=True)
class CrearReservaCommand:
    usuario_id: int
    bloque_id: int
    direccion: str
    zona: str
    lineas: tuple[LineaSolicitada, ...]


@dataclass(frozen=True)
class AbrirDisponibilidadCommand:
    usuario_id: int
    inicio: datetime
    fin: datetime


@dataclass(frozen=True)
class CancelarReservaCommand:
    usuario_id: int
    reserva_id: int
    motivo: str = ""
