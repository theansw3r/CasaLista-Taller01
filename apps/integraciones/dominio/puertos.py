from abc import ABC, abstractmethod

from apps.integraciones.dominio.clima import CondicionesClima


class ProveedorClima(ABC):
    """Puerto (DIP): el caso de uso depende de esto, no de un API concreta."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def condiciones(self) -> CondicionesClima:
        """Devuelve el clima actual o lanza ProveedorNoDisponible."""
