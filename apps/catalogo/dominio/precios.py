from decimal import Decimal

from django.utils.translation import gettext as _

from apps.catalogo.dominio.excepciones import ServicioInactivo
from apps.comun.dominio.dinero import a_dinero


class CalculadoraDeServicio:

    @staticmethod
    def precio(servicio, cantidad: int = 1) -> Decimal:
        return a_dinero(servicio.precio_base * cantidad)

    @staticmethod
    def duracion(servicio, cantidad: int = 1) -> int:
        return servicio.duracion_minutos * cantidad

    @staticmethod
    def exigir_disponible(servicio) -> None:
        if not servicio.activo:
            raise ServicioInactivo(
                _("El servicio '%(servicio)s' ya no está disponible.") % {"servicio": servicio.nombre},
                servicio_id=servicio.pk,
            )
