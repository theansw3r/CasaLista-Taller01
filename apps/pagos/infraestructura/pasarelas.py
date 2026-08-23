"""
Adaptadores del puerto `PasarelaDePago`.

En esta entrega ninguna sale a internet: no hay convenio firmado con un
proveedor real y no tendria sentido bloquear el desarrollo por eso. Lo que si
esta hecho es la SEPARACION: el dia que exista el convenio, se reemplaza el
cuerpo de `cobrar()` por la llamada HTTP real y no cambia nada mas del
sistema, porque nadie fuera de este archivo sabe como se cobra.
"""

import logging
import uuid
from decimal import Decimal

from apps.pagos.dominio.puertos import PasarelaDePago, ResultadoPago

logger = logging.getLogger(__name__)


class PasarelaSimulada(PasarelaDePago):
    """Aprueba siempre. Es la que se usa en desarrollo y en las pruebas."""

    nombre = "SIMULADA"

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        logger.info(
            "[SIMULADA] cobro aprobado por %s (ref interna %s)",
            monto,
            referencia_interna,
        )
        return ResultadoPago(aprobado=True, referencia=f"SIM-{uuid.uuid4().hex[:12]}")


class PasarelaTarjeta(PasarelaDePago):
    """Adaptador para cobros con tarjeta.

    Aqui iria el cliente HTTP del proveedor. Se deja el esqueleto con la
    politica que si es nuestra: el monto minimo que el proveedor acepta. Esa
    validacion vive del lado del adaptador porque es una restriccion DE ESE
    proveedor, no del negocio: otro proveedor tendria otro minimo.
    """

    nombre = "TARJETA"
    MONTO_MINIMO = Decimal("1000.00")

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        if monto < self.MONTO_MINIMO:
            return ResultadoPago(
                aprobado=False,
                motivo=f"El monto minimo con tarjeta es $ {self.MONTO_MINIMO}.",
            )
        # TODO(Entrega 2): reemplazar por la llamada real al proveedor.
        logger.info("[TARJETA] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"TC-{uuid.uuid4().hex[:12]}")


class PasarelaPSE(PasarelaDePago):
    """Adaptador para debito bancario (PSE).

    PSE es asincrono de verdad: el banco confirma por webhook minutos despues.
    Modelarlo bien es trabajo de la Entrega 2; por ahora responde de una vez
    para no bloquear el flujo, y queda anotado.
    """

    nombre = "PSE"

    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        # TODO(Entrega 2): PSE deberia dejar el pago en PENDIENTE y confirmarse
        # por webhook, no responder aprobado en la misma peticion.
        logger.info("[PSE] cobro aprobado por %s", monto)
        return ResultadoPago(aprobado=True, referencia=f"PSE-{uuid.uuid4().hex[:12]}")
