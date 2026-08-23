"""
Calculos monetarios y de duracion de una reserva.

Corresponde a `calcularTotal()` y `duracionTotal()` de Reserva y a
`calcularSubtotal()` de DetalleReserva en el diagrama de dominio.

Sobre la separacion con `tarifas.py`: aqui esta la ARITMETICA (cuanto suman
las lineas) y alli la POLITICA (si a esa suma se le aplica un recargo). Son
dos cosas que cambian por razones distintas: la aritmetica no va a cambiar, la
politica de precios va a cambiar varias veces (es uno de los atributos de
calidad priorizados: modificabilidad).
"""

from decimal import Decimal

from apps.comun.dominio.dinero import CERO, a_dinero


class CalculadoraDeReserva:
    """Suma las lineas de una reserva. No decide recargos ni descuentos."""

    @staticmethod
    def subtotal(detalle) -> Decimal:
        """Precio congelado de la linea por su cantidad."""
        return a_dinero(detalle.precio_unitario * detalle.cantidad)

    @staticmethod
    def duracion_de_linea(detalle) -> int:
        return detalle.duracion_unitaria_minutos * detalle.cantidad

    @classmethod
    def suma_de_lineas(cls, detalles) -> Decimal:
        return a_dinero(sum((cls.subtotal(d) for d in detalles), CERO))

    @classmethod
    def duracion_total(cls, detalles) -> int:
        return sum(cls.duracion_de_linea(d) for d in detalles)

    @classmethod
    def total_de(cls, reserva) -> Decimal:
        """Recalcula el total desde las lineas guardadas.

        No se usa para cobrar (el total se congela al construir la reserva);
        sirve para auditar que el total guardado sigue cuadrando con sus
        lineas.
        """
        return cls.suma_de_lineas(reserva.detalles.all())
