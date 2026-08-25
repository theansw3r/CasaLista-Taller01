from decimal import Decimal

from apps.comun.dominio.dinero import CERO, a_dinero


class CalculadoraDeReserva:

    @staticmethod
    def subtotal(detalle) -> Decimal:
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
        return cls.suma_de_lineas(reserva.detalles.all())
