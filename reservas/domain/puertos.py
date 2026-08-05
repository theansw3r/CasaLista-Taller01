"""
Puertos (interfaces) que el dominio necesita del exterior.

Aplicando el Principio de Inversion de Dependencias, el dominio declara QUE
necesita y la carpeta `infra/` decide COMO se resuelve. Ni el Service ni el
Builder importan una implementacion concreta.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class Notificador(ABC):
    """Puerto de salida para avisarle al cliente que su reserva se creo."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def enviar_confirmacion_reserva(self, reserva) -> None:
        """Notifica la creacion de la reserva. No debe lanzar excepciones."""


class CalculadorTarifa(ABC):
    """Estrategia de calculo del total de una reserva."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def calcular(self, detalles, bloque) -> Decimal:
        """Total a cobrar dadas las lineas y la franja horaria elegida."""
