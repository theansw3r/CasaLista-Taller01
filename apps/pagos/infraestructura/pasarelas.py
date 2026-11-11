import logging
import uuid
from decimal import Decimal

from django.utils.translation import gettext as _

from apps.pagos.dominio.puertos import PasarelaDePago, ResultadoPago

logger = logging.getLogger(__name__)


class PasarelaSimulada(PasarelaDePago):

    nombre = "SIMULADA"

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        logger.info(
            "[SIMULADA] cobro aprobado por %s (ref interna %s)",
            monto,
            referencia_interna,
        )
        return ResultadoPago(aprobado=True, referencia=f"SIM-{uuid.uuid4().hex[:12]}")


class PasarelaTarjeta(PasarelaDePago):

    nombre = "TARJETA"
    MONTO_MINIMO = Decimal("1000.00")

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        if monto < self.MONTO_MINIMO:
            return ResultadoPago(
                aprobado=False,
                motivo=_("El monto mínimo con tarjeta es $ %(monto)s.") % {"monto": self.MONTO_MINIMO},
            )
        logger.info("[TARJETA] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"TC-{uuid.uuid4().hex[:12]}")


class PasarelaPSE(PasarelaDePago):

    nombre = "PSE"

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        logger.info("[PSE] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"PSE-{uuid.uuid4().hex[:12]}")
