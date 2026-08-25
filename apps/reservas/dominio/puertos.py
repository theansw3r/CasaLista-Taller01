from abc import ABC, abstractmethod
from decimal import Decimal


class Notificador(ABC):

    nombre = "ABSTRACTO"

    @abstractmethod
    def enviar_confirmacion_reserva(self, reserva) -> None:
        pass


class CalculadorTarifa(ABC):

    nombre = "ABSTRACTO"

    @abstractmethod
    def calcular(self, detalles, bloque) -> Decimal:
        pass


class PoliticaDeCancelacion(ABC):

    nombre = "ABSTRACTO"

    @abstractmethod
    def calcular_penalizacion(self, reserva, momento) -> Decimal:
        pass
