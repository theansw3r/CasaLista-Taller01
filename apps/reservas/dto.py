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
