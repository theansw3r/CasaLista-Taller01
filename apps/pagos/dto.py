from dataclasses import dataclass


@dataclass(frozen=True)
class ProcesarPagoCommand:
    usuario_id: int
    reserva_id: int
    medio: str
