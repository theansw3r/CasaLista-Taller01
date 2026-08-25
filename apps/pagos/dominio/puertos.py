from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResultadoPago:

    aprobado: bool
    referencia: str = ""
    motivo: str = ""


class PasarelaDePago(ABC):

    nombre = "ABSTRACTA"

    @abstractmethod
    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        pass
