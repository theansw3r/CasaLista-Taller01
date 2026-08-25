from decimal import Decimal

from django.utils import timezone

from apps.comun.dominio.dinero import a_dinero
from apps.reservas.dominio.precios import CalculadoraDeReserva
from apps.reservas.dominio.puertos import CalculadorTarifa


class TarifaBase(CalculadorTarifa):

    nombre = "BASE"

    def calcular(self, detalles, bloque) -> Decimal:
        return CalculadoraDeReserva.suma_de_lineas(detalles)


class TarifaDinamica(TarifaBase):

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
        es_nocturno = (
            inicio.hour >= self.HORA_DESDE_NOCTURNO
            or inicio.hour < self.HORA_HASTA_NOCTURNO
        )
        if es_nocturno:
            factor += self.RECARGO_NOCTURNO
        if inicio.weekday() >= 5:
            factor += self.RECARGO_FIN_DE_SEMANA
        return factor

    @staticmethod
    def _hora_local(momento):
        return timezone.localtime(momento) if timezone.is_aware(momento) else momento
