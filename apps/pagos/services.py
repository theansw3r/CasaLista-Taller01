"""
Capa de aplicacion del modulo Pagos.

Este servicio implementa RN-03: "una reserva solo puede confirmarse si existe
un pago aprobado asociado". Es el paso 3 del flujo nucleo del Business Case
(seccion 1.5).

Es el segundo caso de uso mas interesante de la arquitectura porque coordina
DOS modulos: cobra en el suyo y pide una transicion de estado en el de
reservas. Y lo hace sin acoplarse: no toca `Reserva.estado` a mano, le pide a
`CicloDeVidaReserva` que confirme. Si manana confirmar exigiera algo mas, ese
algo mas se escribe en un solo sitio.
"""

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
    """Caso de uso: el cliente paga su reserva y esta queda confirmada."""

    def __init__(
        self,
        pasarela: PasarelaDePago | None = None,
        consultas: ConsultaReservasService | None = None,
    ) -> None:
        # `pasarela=None` significa "resuelvela cuando sepas el medio". En las
        # pruebas se inyecta una pasarela falsa y la Factory ni se consulta.
        self.pasarela = pasarela
        self.consultas = consultas or ConsultaReservasService()

    def procesar(self, comando: ProcesarPagoCommand) -> Pago:
        """Cobra y confirma. Cuatro pasos, en este orden y por esta razon."""
        # 1. La reserva tiene que existir, ser del cliente y estar cobrable.
        #    Se valida ANTES de cobrar: nunca se le mueve plata a alguien para
        #    despues descubrir que la reserva no era suya.
        reserva = self.consultas.detalle_de(comando.usuario_id, comando.reserva_id)
        self._exigir_cobrable(reserva)

        # 2. Se cobra fuera de la transaccion. Una llamada de red puede tardar
        #    segundos, y mantener filas bloqueadas mientras tanto degradaria
        #    toda la agenda.
        pasarela = self.pasarela or PasarelaPagoFactory.para_medio(comando.medio)
        resultado = pasarela.cobrar(
            monto=a_dinero(reserva.total),
            referencia_interna=f"reserva-{reserva.pk}",
        )

        # 3. Un rechazo tambien se guarda: un pago rechazado es informacion de
        #    negocio, no un no-evento. Sin el no se puede reintentar ni saber
        #    por que un cliente no pudo pagar.
        if not resultado.aprobado:
            self._registrar_rechazo(reserva, comando.medio, pasarela, resultado)
            raise PagoRechazado(
                resultado.motivo or "La pasarela rechazo el pago.",
                reserva_id=reserva.pk,
            )

        # 4. Guardar el pago y confirmar la reserva son un solo hecho (RN-03).
        return self._registrar_aprobacion(reserva, comando.medio, pasarela, resultado)

    # ------------------------------------------------------------------
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
            # RN-03: la confirmacion la autoriza el pago, pero quien sabe si
            # la reserva puede pasar a CONFIRMADA es el modulo de reservas.
            CicloDeVidaReserva.confirmar(reserva)
            reserva.save(update_fields=["estado", "actualizada_en"])
        return pago


class ConsultaPagosService:
    """Caso de uso de lectura: el cliente consulta un pago suyo."""

    def __init__(self, consultas: ConsultaReservasService | None = None) -> None:
        self.consultas = consultas or ConsultaReservasService()

    def detalle_de(self, usuario_id: int, pago_id: int) -> Pago:
        try:
            pago = Pago.objects.select_related("reserva").get(pk=pago_id)
        except Pago.DoesNotExist:
            raise PagoNoEncontrado(
                f"No existe el pago {pago_id}.", pago_id=pago_id
            ) from None
        # Se reutiliza la comprobacion de propiedad del modulo de reservas en
        # vez de reimplementarla: un pago es privado porque su reserva lo es.
        self.consultas.detalle_de(usuario_id, pago.reserva_id)
        return pago
