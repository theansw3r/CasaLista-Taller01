from django.utils.translation import gettext as _

from apps.reservas.dominio.excepciones import TransicionDeEstadoInvalida
from apps.reservas.models import Reserva

Estado = Reserva.Estado

TRANSICIONES_PERMITIDAS: dict[str, set[str]] = {
    Estado.PENDIENTE: {Estado.CONFIRMADA, Estado.CANCELADA},
    Estado.CONFIRMADA: {Estado.COMPLETADA, Estado.CANCELADA},
    Estado.COMPLETADA: set(),
    Estado.CANCELADA: set(),
}

ESTADOS_ACTIVOS = (Estado.PENDIENTE, Estado.CONFIRMADA)


class CicloDeVidaReserva:

    @staticmethod
    def esta_activa(reserva) -> bool:
        return reserva.estado in ESTADOS_ACTIVOS

    @classmethod
    def puede_pasar_a(cls, reserva, nuevo_estado: str) -> bool:
        return nuevo_estado in TRANSICIONES_PERMITIDAS.get(reserva.estado, set())

    @classmethod
    def _transicionar(cls, reserva, nuevo_estado: str) -> None:
        if not cls.puede_pasar_a(reserva, nuevo_estado):
            raise TransicionDeEstadoInvalida(
                _("Una reserva %(estado_actual)s no puede pasar a %(estado_nuevo)s.") % {"estado_actual": reserva.get_estado_display().lower(), "estado_nuevo": Estado(nuevo_estado).label.lower()},
                estado_actual=reserva.estado,
                estado_solicitado=nuevo_estado,
            )
        reserva.estado = nuevo_estado

    @classmethod
    def confirmar(cls, reserva) -> None:
        cls._transicionar(reserva, Estado.CONFIRMADA)

    @classmethod
    def completar(cls, reserva) -> None:
        cls._transicionar(reserva, Estado.COMPLETADA)

    @classmethod
    def cancelar(cls, reserva) -> None:
        cls._transicionar(reserva, Estado.CANCELADA)
