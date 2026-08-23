"""
Ciclo de vida de una Reserva.

Corresponde a `confirmar()` y `cancelar()` del diagrama. Estan aqui y no en el
modelo por la misma razon de siempre: son reglas, no persistencia.

El grafo de transiciones se declara como un diccionario en vez de repartirse
en `if`. Asi la maquina de estados se lee de un vistazo y agregar un estado
nuevo (por ejemplo EN_CURSO) es agregar una fila, no rastrear condicionales:

    PENDIENTE  -> CONFIRMADA | CANCELADA
    CONFIRMADA -> COMPLETADA | CANCELADA
    COMPLETADA -> (final)
    CANCELADA  -> (final)

Los metodos cambian el objeto EN MEMORIA. Guardar es responsabilidad de quien
llama (el servicio), que es quien controla la transaccion.
"""

from apps.reservas.dominio.excepciones import TransicionDeEstadoInvalida
from apps.reservas.models import Reserva

Estado = Reserva.Estado

TRANSICIONES_PERMITIDAS: dict[str, set[str]] = {
    Estado.PENDIENTE: {Estado.CONFIRMADA, Estado.CANCELADA},
    Estado.CONFIRMADA: {Estado.COMPLETADA, Estado.CANCELADA},
    Estado.COMPLETADA: set(),
    Estado.CANCELADA: set(),
}

# Estados en los que la reserva todavia ocupa la agenda del profesional.
ESTADOS_ACTIVOS = (Estado.PENDIENTE, Estado.CONFIRMADA)


class CicloDeVidaReserva:
    """Unico lugar donde una reserva cambia de estado."""

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
                f"Una reserva {reserva.get_estado_display().lower()} no puede "
                f"pasar a {Estado(nuevo_estado).label.lower()}.",
                estado_actual=reserva.estado,
                estado_solicitado=nuevo_estado,
            )
        reserva.estado = nuevo_estado

    # ------------------------------------------------------------------
    # Transiciones del negocio
    # ------------------------------------------------------------------
    @classmethod
    def confirmar(cls, reserva) -> None:
        """RN-03: solo se llama cuando ya existe un pago aprobado.

        Quien comprueba el pago es el modulo de Pagos: este modulo no conoce
        la clase Pago, y esa ignorancia es lo que permitiria extraer Pagos a
        un servicio aparte mas adelante.
        """
        cls._transicionar(reserva, Estado.CONFIRMADA)

    @classmethod
    def completar(cls, reserva) -> None:
        cls._transicionar(reserva, Estado.COMPLETADA)

    @classmethod
    def cancelar(cls, reserva) -> None:
        cls._transicionar(reserva, Estado.CANCELADA)
