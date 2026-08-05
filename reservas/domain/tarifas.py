"""
Estrategias de tarifa.

Son dominio puro: no consultan la base de datos ni conocen Django. Reciben las
lineas (aun sin guardar) y el bloque, y devuelven el total.
"""

from decimal import Decimal

from django.utils import timezone

from .dinero import a_dinero
from .puertos import CalculadorTarifa


class TarifaBase(CalculadorTarifa):
    """Total = suma de los subtotales con el precio congelado en cada linea."""

    nombre = "BASE"

    def calcular(self, detalles, bloque) -> Decimal:
        subtotales = (detalle.calcular_subtotal() for detalle in detalles)
        return a_dinero(sum(subtotales, Decimal("0")))


class TarifaDinamica(TarifaBase):
    """Aplica recargos segun cuando se agenda la visita.

    Las franjas nocturnas y de fin de semana son las mas escasas de la agenda,
    asi que se cobran mas caras (seccion 1.3 del Business Case).
    """

    nombre = "DINAMICA"

    RECARGO_NOCTURNO = Decimal("0.20")
    RECARGO_FIN_DE_SEMANA = Decimal("0.15")
    HORA_DESDE_NOCTURNO = 19
    HORA_HASTA_NOCTURNO = 7

    def calcular(self, detalles, bloque) -> Decimal:
        subtotal = super().calcular(detalles, bloque)
        return a_dinero(subtotal * self._factor(bloque))

    def _factor(self, bloque) -> Decimal:
        inicio = self._hora_local(bloque.inicio)
        factor = Decimal("1")
        if inicio.hour >= self.HORA_DESDE_NOCTURNO or inicio.hour < self.HORA_HASTA_NOCTURNO:
            factor += self.RECARGO_NOCTURNO
        if inicio.weekday() >= 5:
            factor += self.RECARGO_FIN_DE_SEMANA
        return factor

    @staticmethod
    def _hora_local(momento):
        return timezone.localtime(momento) if timezone.is_aware(momento) else momento
