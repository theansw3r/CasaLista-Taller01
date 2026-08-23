"""
Puertos del modulo de Reservas.

Un puerto es una interfaz que el dominio declara para decir QUE necesita del
mundo exterior, sin decir COMO se resuelve. Las implementaciones viven en
`infraestructura/` y las elige una Factory.

Esto es el Principio de Inversion de Dependencias en concreto: el Service y el
Builder importan de este archivo, nunca de `infraestructura/`. La flecha de
dependencia apunta siempre hacia el dominio, y por eso el dominio se puede
probar sin correo, sin pasarela y sin base de datos.

Cada puerto tiene un solo metodo (Segregacion de Interfaces): quien solo
necesita notificar no queda obligado a implementar tambien el calculo de
tarifa.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class Notificador(ABC):
    """Puerto de salida: avisarle al cliente que su reserva se creo."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def enviar_confirmacion_reserva(self, reserva) -> None:
        """Notifica la creacion de la reserva.

        Contrato: no debe lanzar excepciones. Una notificacion que falla no
        puede tumbar una reserva que ya se guardo; el negocio prefiere una
        reserva sin correo que un cliente sin reserva.
        """


class CalculadorTarifa(ABC):
    """Puerto de politica: cuanto se cobra por unas lineas en una franja."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def calcular(self, detalles, bloque) -> Decimal:
        """Total a cobrar dadas las lineas y la franja horaria elegida.

        Recibe los detalles todavia sin guardar, por lo que la estrategia
        puede evaluarse antes de tocar la base de datos.
        """


class PoliticaDeCancelacion(ABC):
    """Puerto de politica: cuanto se retiene si el cliente cancela (RN-04)."""

    nombre = "ABSTRACTO"

    @abstractmethod
    def calcular_penalizacion(self, reserva, momento) -> Decimal:
        """Monto retenido al cancelar `reserva` en `momento`."""
