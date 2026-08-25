from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.comun.dominio.dinero import CERO, a_dinero, porcentaje_de
from apps.reservas.dominio.agenda import ReglasAgenda
from apps.reservas.dominio.puertos import PoliticaDeCancelacion


class PoliticaDeCancelacionEstandar(PoliticaDeCancelacion):

    nombre = "ESTANDAR"

    def calcular_penalizacion(self, reserva, momento=None) -> Decimal:
        ahora = momento or timezone.now()
        horas_restantes = ReglasAgenda.horas_hasta(reserva.bloque, ahora)

        if horas_restantes >= settings.HORAS_CANCELACION_SIN_PENALIZACION:
            return CERO
        if horas_restantes >= settings.HORAS_CANCELACION_PENALIZACION_PARCIAL:
            return porcentaje_de(reserva.total, settings.PENALIZACION_PARCIAL)
        return a_dinero(reserva.total)
