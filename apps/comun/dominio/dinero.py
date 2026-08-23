"""
Manejo de dinero.

Esta en el dominio compartido y no en un `utils.py` porque redondear a dos
decimales con HALF_UP es una decision del negocio (asi factura la plataforma),
no un detalle tecnico. Tres modulos distintos calculan plata (catalogo,
reservas y pagos) y los tres tienen que redondear igual.

Se usa Decimal y nunca float: 0.1 + 0.2 en float no da 0.3, y en una factura
eso es un centavo perdido que despues no cuadra en la liquidacion.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")
CERO = Decimal("0.00")


def a_dinero(valor) -> Decimal:
    """Normaliza cualquier calculo monetario a dos decimales (HALF_UP)."""
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def porcentaje_de(monto: Decimal, proporcion: Decimal) -> Decimal:
    """Aplica una proporcion (0.12 = 12 %) sobre un monto y redondea."""
    return a_dinero(Decimal(monto) * Decimal(proporcion))
