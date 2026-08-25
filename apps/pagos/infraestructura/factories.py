from apps.comun.infraestructura.factory import FactoryPorEntorno
from apps.pagos.dominio.puertos import PasarelaDePago
from apps.pagos.infraestructura.pasarelas import (
    PasarelaPSE,
    PasarelaSimulada,
    PasarelaTarjeta,
)


class PasarelaPagoFactory(FactoryPorEntorno):

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
        if cls.configuracion_actual().strip().upper() == "SIMULADA":
            return cls.crear("SIMULADA")
        return cls.crear(medio)
