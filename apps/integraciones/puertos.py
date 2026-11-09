from typing import Protocol


class ProveedorClima(Protocol):
    def condiciones(self) -> dict: ...
