"""
Factory de pasarelas de pago.

Es el caso de uso mas literal del patron: una dependencia externa con varias
variantes, donde quien la necesita no debe saber cual esta usando.

    PASARELA_PAGO_TYPE=SIMULADA  ->  PasarelaSimulada   (desarrollo y pruebas)
    PASARELA_PAGO_TYPE=TARJETA   ->  PasarelaTarjeta
    PASARELA_PAGO_TYPE=PSE       ->  PasarelaPSE

Esta Factory tiene una diferencia con las de reservas: ademas del valor del
entorno acepta que el llamador pida una variante concreta. Es necesario
porque aqui la eleccion no siempre es del entorno; a veces es del cliente, que
en el formulario escoge si paga con tarjeta o con PSE. `medio` viaja como dato
de la peticion y la Factory lo resuelve igual, sin que el Service conozca
ninguna clase concreta.
"""

from apps.comun.infraestructura.factory import FactoryPorEntorno
from apps.pagos.dominio.puertos import PasarelaDePago
from apps.pagos.infraestructura.pasarelas import (
    PasarelaPSE,
    PasarelaSimulada,
    PasarelaTarjeta,
)


class PasarelaPagoFactory(FactoryPorEntorno):
    """Devuelve la pasarela pedida, o la que dicte PASARELA_PAGO_TYPE."""

    variable_de_entorno = "PASARELA_PAGO_TYPE"
    valor_por_defecto = "SIMULADA"
    registro = {
        "SIMULADA": PasarelaSimulada,
        "TARJETA": PasarelaTarjeta,
        "PSE": PasarelaPSE,
    }

    @classmethod
    def crear(cls, tipo: str | None = None) -> PasarelaDePago:
        return super().crear(tipo)

    @classmethod
    def para_medio(cls, medio: str) -> PasarelaDePago:
        """Resuelve la pasarela a partir del medio que eligio el cliente.

        En desarrollo el entorno fuerza SIMULADA para no cobrarle a nadie de
        verdad; en produccion se respeta lo que pidio el cliente.
        """
        if cls.configuracion_actual().strip().upper() == "SIMULADA":
            return cls.crear("SIMULADA")
        return cls.crear(medio)
