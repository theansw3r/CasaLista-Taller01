import logging

from django.db import transaction

from apps.comun.dominio.dinero import a_dinero
from apps.pagos.dominio.excepciones import (
    PagoNoEncontrado,
    PagoRechazado,
    ReservaNoCobrable,
    ReservaYaPagada,
)
from apps.pagos.dominio.puertos import PasarelaDePago
from apps.pagos.dto import ProcesarPagoCommand
from apps.pagos.infraestructura.factories import PasarelaPagoFactory
from apps.pagos.models import Pago
from apps.reservas.dominio.ciclo_de_vida import CicloDeVidaReserva
from apps.reservas.models import Reserva
from apps.reservas.services import ConsultaReservasService

logger = logging.getLogger(__name__)


class PagoService:

    def __init__(
        self,
        pasarela: PasarelaDePago | None = None,
        consultas: ConsultaReservasService | None = None,
    ) -> None:
        self.pasarela = pasarela
        self.consultas = consultas or ConsultaReservasService()

    def procesar(self, comando: ProcesarPagoCommand) -> Pago:
        reserva = self.consultas.detalle_de(comando.usuario_id, comando.reserva_id)
        self._exigir_cobrable(reserva)

        pasarela = self.pasarela or PasarelaPagoFactory.para_medio(comando.medio)
        resultado = pasarela.cobrar(
            monto=a_dinero(reserva.total),
            referencia_interna=f"reserva-{reserva.pk}",
        )

        if not resultado.aprobado:
            self._registrar_rechazo(reserva, comando.medio, pasarela, resultado)
            raise PagoRechazado(
                resultado.motivo or "La pasarela rechazo el pago.",
                reserva_id=reserva.pk,
            )

        return self._registrar_aprobacion(reserva, comando.medio, pasarela, resultado)

    @staticmethod
    def _exigir_cobrable(reserva: Reserva) -> None:
        if reserva.estado != Reserva.Estado.PENDIENTE:
            raise ReservaNoCobrable(
                f"La reserva #{reserva.pk} esta "
                f"{reserva.get_estado_display().lower()} y no admite pago.",
                estado_actual=reserva.estado,
            )
        if Pago.objects.filter(reserva=reserva).exists():
            raise ReservaYaPagada(reserva_id=reserva.pk)

    @staticmethod
    def _registrar_rechazo(reserva, medio, pasarela, resultado) -> Pago:
        logger.warning(
            "Pago rechazado para reserva %s por %s: %s",
            reserva.pk,
            pasarela.nombre,
            resultado.motivo,
        )
        return Pago.objects.create(
            reserva=reserva,
            monto=a_dinero(reserva.total),
            medio=medio,
            pasarela=pasarela.nombre,
            estado=Pago.Estado.RECHAZADO,
            motivo_rechazo=resultado.motivo[:200],
        )

    @staticmethod
    def _registrar_aprobacion(reserva, medio, pasarela, resultado) -> Pago:
        with transaction.atomic():
            pago = Pago.objects.create(
                reserva=reserva,
                monto=a_dinero(reserva.total),
                medio=medio,
                pasarela=pasarela.nombre,
                estado=Pago.Estado.APROBADO,
                referencia_externa=resultado.referencia,
            )
            CicloDeVidaReserva.confirmar(reserva)
            reserva.save(update_fields=["estado", "actualizada_en"])
        return pago


class ConsultaPagosService:

    def __init__(self, consultas: ConsultaReservasService | None = None) -> None:
        self.consultas = consultas or ConsultaReservasService()

    def detalle_de(self, usuario_id: int, pago_id: int) -> Pago:
        try:
            pago = Pago.objects.select_related("reserva").get(pk=pago_id)
        except Pago.DoesNotExist:
            raise PagoNoEncontrado(
                f"No existe el pago {pago_id}.", pago_id=pago_id
            ) from None
        self.consultas.detalle_de(usuario_id, pago.reserva_id)
        return pago
