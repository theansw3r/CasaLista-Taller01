from apps.integraciones.puertos import ProveedorClima


class ConsultaClimaService:
    # DIP: el caso de uso recibe un puerto y desconoce HTTP/Open-Meteo.
    def __init__(self, proveedor: ProveedorClima):
        self.proveedor = proveedor

    def consultar(self):
        return self.proveedor.condiciones()
