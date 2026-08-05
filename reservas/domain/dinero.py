"""Normalizacion monetaria. Vive en el dominio porque es una regla del negocio,
no un detalle de la base de datos."""

from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")


def a_dinero(valor) -> Decimal:
    """Redondea cualquier calculo monetario a dos decimales (HALF_UP)."""
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
