"""
Politica de cancelacion (RN-04).

    mas de 24 h antes  -> sin penalizacion
    entre 24 h y 2 h   -> se retiene el 30 %
    menos de 2 h       -> no hay reembolso (se retiene el 100 %)

Se implementa como una clase que cumple el puerto `PoliticaDeCancelacion` y no
como una funcion suelta, por dos motivos:

1. Los porcentajes y las ventanas se leen de settings, asi que el area de
   negocio puede ajustarlos sin desplegar codigo nuevo.
2. El dia que exista una politica distinta (por ejemplo una mas blanda para
   clientes frecuentes), se escribe otra clase que cumpla el mismo puerto y se
   inyecta en el servicio. Nada mas cambia.
"""

from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.comun.dominio.dinero import CERO, a_dinero, porcentaje_de
from apps.reservas.dominio.agenda import ReglasAgenda
from apps.reservas.dominio.puertos import PoliticaDeCancelacion


class PoliticaDeCancelacionEstandar(PoliticaDeCancelacion):
    """La politica publicada en los terminos y condiciones."""

    nombre = "ESTANDAR"

    def calcular_penalizacion(self, reserva, momento=None) -> Decimal:
        ahora = momento or timezone.now()
        horas_restantes = ReglasAgenda.horas_hasta(reserva.bloque, ahora)

        if horas_restantes >= settings.HORAS_CANCELACION_SIN_PENALIZACION:
            return CERO
        if horas_restantes >= settings.HORAS_CANCELACION_PENALIZACION_PARCIAL:
            return porcentaje_de(reserva.total, settings.PENALIZACION_PARCIAL)
        # Menos de dos horas (o la visita ya paso): no hay reembolso.
        return a_dinero(reserva.total)
