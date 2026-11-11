from apps.integraciones.dominio.clima import CondicionesClima
from apps.integraciones.dominio.excepciones import AliadoNoConfigurado
from apps.integraciones.dominio.puertos import ProveedorClima


class ConsultaClimaService:
    """Caso de uso. Recibe el puerto inyectado y no sabe nada de HTTP."""

    def __init__(self, proveedor: ProveedorClima) -> None:
        self.proveedor = proveedor

    def consultar(self) -> CondicionesClima:
        return self.proveedor.condiciones()


class ConsultaAliadoService:
    """Pendiente: no se inventa el contrato ni los datos de otro equipo.

    Cuando el aliado entregue URL, esquema y autenticacion, este caso de uso
    recibe su puerto igual que ConsultaClimaService.
    """

    def consultar(self):
        raise AliadoNoConfigurado()
