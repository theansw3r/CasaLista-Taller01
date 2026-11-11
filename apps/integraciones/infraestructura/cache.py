from django.core.cache import cache

from apps.integraciones.dominio.clima import CondicionesClima
from apps.integraciones.dominio.puertos import ProveedorClima


class ProveedorClimaEnCache(ProveedorClima):
    """Decorator: envuelve a otro proveedor y guarda su respuesta un rato.

    Implementa el mismo puerto, asi que el caso de uso no sabe si hay cache o
    no. Solo se guardan respuestas buenas: si el tercero falla, la excepcion
    sube y el proximo pedido vuelve a intentar.
    """

    nombre = "CACHE"

    def __init__(self, proveedor: ProveedorClima, clave: str, segundos: int) -> None:
        self.proveedor = proveedor
        self.clave = clave
        self.segundos = segundos

    def condiciones(self) -> CondicionesClima:
        guardado = cache.get(self.clave)
        if guardado is not None:
            return guardado
        condiciones = self.proveedor.condiciones()
        cache.set(self.clave, condiciones, timeout=self.segundos)
        return condiciones
