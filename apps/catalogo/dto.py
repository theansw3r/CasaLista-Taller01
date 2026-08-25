from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PublicarServicioCommand:
    usuario_id: int
    categoria: str
    nombre: str
    descripcion: str
    precio_base: Decimal
    duracion_minutos: int
    requiere_visita_previa: bool = False
