from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.utils import timezone

from apps.reservas.dominio.excepciones import (
    BloqueNoDisponible,
    BloquesSolapados,
    RangoHorarioInvalido,
)
from apps.reservas.models import BloqueDisponibilidad, Reserva

ESTADOS_QUE_OCUPAN_AGENDA = (Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA)


class ReglasAgenda:

    @staticmethod
    def duracion_minutos(bloque) -> int:
        return int((bloque.fin - bloque.inicio).total_seconds() // 60)

    @staticmethod
    def esta_libre(bloque) -> bool:
        return bloque.estado == BloqueDisponibilidad.Estado.LIBRE

    @staticmethod
    def se_solapan(uno, otro) -> bool:
        return uno.inicio < otro.fin and otro.inicio < uno.fin

    @staticmethod
    def horas_hasta(bloque, momento=None) -> float:
        ahora = momento or timezone.now()
        return (bloque.inicio - ahora).total_seconds() / 3600

    @classmethod
    def exigir_rango_valido(cls, inicio, fin) -> None:
        if fin <= inicio:
            raise RangoHorarioInvalido(
                _("La franja debe terminar despues de empezar."),
                inicio=inicio.isoformat(),
                fin=fin.isoformat(),
            )

    @classmethod
    def exigir_sin_solapamiento(cls, profesional, inicio, fin) -> None:
        hay_choque = BloqueDisponibilidad.objects.filter(
            profesional=profesional, inicio__lt=fin, fin__gt=inicio
        ).exists()
        if hay_choque:
            raise BloquesSolapados(
                _("El profesional ya tiene una franja publicada en ese horario."),
                inicio=inicio.isoformat(),
                fin=fin.isoformat(),
            )

    @classmethod
    def exigir_disponible(cls, bloque) -> None:
        if not cls.esta_libre(bloque):
            raise BloqueNoDisponible(
                _("La franja horaria ya fue tomada."), bloque_id=bloque.pk
            )
        ya_reservado = Reserva.objects.filter(
            bloque=bloque, estado__in=ESTADOS_QUE_OCUPAN_AGENDA
        ).exists()
        if ya_reservado:
            raise BloqueNoDisponible(
                _("La franja horaria ya tiene una reserva activa."), bloque_id=bloque.pk
            )

    @staticmethod
    def ocupar(bloque) -> None:
        bloque.estado = BloqueDisponibilidad.Estado.OCUPADO

    @staticmethod
    def liberar(bloque) -> None:
        bloque.estado = BloqueDisponibilidad.Estado.LIBRE
