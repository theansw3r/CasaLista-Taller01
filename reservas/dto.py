"""
Objetos de transporte entre la capa de interfaz y la de aplicacion.

El Service recibe un `CrearReservaCommand`, no un `HttpRequest`. Gracias a eso
el mismo caso de uso sirve para una vista web, un comando de management o una
API REST sin cambiar una linea.
"""

from dataclasses import dataclass


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
