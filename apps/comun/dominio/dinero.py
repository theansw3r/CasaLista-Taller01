from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")
CERO = Decimal("0.00")


def a_dinero(valor) -> Decimal:
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def porcentaje_de(monto: Decimal, proporcion: Decimal) -> Decimal:
    return a_dinero(Decimal(monto) * Decimal(proporcion))
