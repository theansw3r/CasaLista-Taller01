"""
Precio de un servicio del catalogo.

`calcularPrecio()` aparece en el diagrama como metodo de Servicio. Se saca del
modelo porque es un calculo, y los calculos dentro de un modelo lo convierten
en un "fat model": la clase que persiste pasa a decidir cuanto se cobra.

Es una clase sin estado (todo `staticmethod`): recibe la entidad, devuelve el
numero. Se prueba sin base de datos.
"""

from decimal import Decimal

from apps.catalogo.dominio.excepciones import ServicioInactivo
from apps.comun.dominio.dinero import a_dinero


class CalculadoraDeServicio:
    """Precio y duracion de un servicio del catalogo para una cantidad dada."""

    @staticmethod
    def precio(servicio, cantidad: int = 1) -> Decimal:
        return a_dinero(servicio.precio_base * cantidad)

    @staticmethod
    def duracion(servicio, cantidad: int = 1) -> int:
        return servicio.duracion_minutos * cantidad

    @staticmethod
    def exigir_disponible(servicio) -> None:
        """Un servicio dado de baja no se puede reservar.

        Se comprueba al reservar y no al listar, porque el catalogo se puede
        haber leido de una cache y el servicio pudo desactivarse despues.
        """
        if not servicio.activo:
            raise ServicioInactivo(
                f"El servicio '{servicio.nombre}' ya no esta disponible.",
                servicio_id=servicio.pk,
            )
