from apps.integraciones.dominio.puertos import ProveedorClima
from apps.integraciones.infraestructura.cache import ProveedorClimaEnCache
from apps.integraciones.infraestructura.open_meteo import OpenMeteoAdapter

CLAVE_CACHE_CLIMA = "integraciones:clima:medellin:v2"
SEGUNDOS_CACHE_CLIMA = 300


def crear_proveedor_clima() -> ProveedorClima:
    """Punto de composicion: el unico lugar que conoce las clases concretas."""
    return ProveedorClimaEnCache(
        OpenMeteoAdapter(),
        clave=CLAVE_CACHE_CLIMA,
        segundos=SEGUNDOS_CACHE_CLIMA,
    )
