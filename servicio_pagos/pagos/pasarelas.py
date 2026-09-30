import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoPago:
    aprobado: bool
    referencia: str = ""
    motivo: str = ""


class PasarelaDePago(ABC):

    nombre = "ABSTRACTA"

    @abstractmethod
    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        pass


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
                motivo=f"El monto minimo con tarjeta es $ {self.MONTO_MINIMO}.",
            )
        logger.info("[TARJETA] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"TC-{uuid.uuid4().hex[:12]}")


class PasarelaPSE(PasarelaDePago):

    nombre = "PSE"

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        logger.info("[PSE] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"PSE-{uuid.uuid4().hex[:12]}")


REGISTRO = {
    "SIMULADA": PasarelaSimulada,
    "TARJETA": PasarelaTarjeta,
    "PSE": PasarelaPSE,
}


def pasarela_para(medio: str, configuracion: str) -> PasarelaDePago:
    # Igual que PasarelaPagoFactory.para_medio en Django: con SIMULADA se
    # ignora el medio que pidio el cliente, para no cobrarle de verdad a nadie
    # mientras se desarrolla.
    if configuracion.strip().upper() == "SIMULADA":
        return PasarelaSimulada()
    return REGISTRO[medio]()
