"""
Estrategias de tarifa (implementaciones del puerto `CalculadorTarifa`).

Son dominio puro: no consultan la base de datos, no conocen HTTP y no importan
nada de `infraestructura/`. Reciben las lineas todavia en memoria y la franja,
y devuelven el total.

Cual de las dos se usa lo decide `CalculadorTarifaFactory` leyendo
TARIFA_TYPE. Agregar una tercera (por ejemplo TarifaPromocional) es escribir
una clase aqui y una entrada en el registro de la Factory: ni el Service ni el
Builder se enteran (Abierto/Cerrado).
"""

from decimal import Decimal

from django.utils import timezone

from apps.comun.dominio.dinero import a_dinero
from apps.reservas.dominio.precios import CalculadoraDeReserva
from apps.reservas.dominio.puertos import CalculadorTarifa


class TarifaBase(CalculadorTarifa):
    """Total = suma de los subtotales con el precio congelado en cada linea."""

    nombre = "BASE"

    def calcular(self, detalles, bloque) -> Decimal:
        return CalculadoraDeReserva.suma_de_lineas(detalles)


class TarifaDinamica(TarifaBase):
    """Recarga las franjas escasas.

    Las noches y los fines de semana son los horarios que menos profesionales
    publican y los que mas clientes piden (seccion 1.3 del Business Case), asi
    que se cobran mas caros.

    Hereda de TarifaBase en vez de reimplementar la suma: el recargo es una
    capa SOBRE el calculo base, no un calculo distinto.
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
        es_nocturno = (
            inicio.hour >= self.HORA_DESDE_NOCTURNO
            or inicio.hour < self.HORA_HASTA_NOCTURNO
        )
        if es_nocturno:
            factor += self.RECARGO_NOCTURNO
        if inicio.weekday() >= 5:  # sabado y domingo
            factor += self.RECARGO_FIN_DE_SEMANA
        return factor

    @staticmethod
    def _hora_local(momento):
        """Convierte a la zona del negocio antes de mirar la hora.

        Django guarda los datetime en UTC. Preguntar `momento.hour` sobre el
        valor crudo diria que las 8 de la noche en Medellin es la una de la
        madrugada, y aplicaria el recargo nocturno cuando no toca.
        """
        return timezone.localtime(momento) if timezone.is_aware(momento) else momento
