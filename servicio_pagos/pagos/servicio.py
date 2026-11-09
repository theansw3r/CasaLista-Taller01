from pagos.i18n import gettext as _, marcar as _lazy
import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pagos.errores import (
    ErrorDePagos,
    PagoNoEncontrado,
    PagoRechazado,
    ReservaNoCobrable,
    ReservaSinConfirmar,
    ReservaYaPagada,
)
from pagos.modelos import Pago, db
from pagos.pasarelas import pasarela_para

logger = logging.getLogger(__name__)

CENTAVOS = Decimal("0.01")
ETIQUETAS_ESTADO = {
    "PENDIENTE": _lazy("Pendiente de pago"),
    "CONFIRMADA": _lazy("Confirmada"),
    "COMPLETADA": _lazy("Completada"),
    "CANCELADA": _lazy("Cancelada"),
}


def a_dinero(valor) -> Decimal:
    return Decimal(str(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ProcesarPagoCommand:
    reserva_id: int
    medio: str
    autorizacion: str
    id_peticion: str = ""


class PagoService:

    def __init__(self, reservas, configuracion_pasarela: str = "SIMULADA") -> None:
        self.reservas = reservas
        self.configuracion_pasarela = configuracion_pasarela

    def procesar(self, comando: ProcesarPagoCommand) -> tuple[Pago, str]:
        reserva = self.reservas.obtener(
            comando.reserva_id, comando.autorizacion, comando.id_peticion
        )
        self._exigir_cobrable(reserva)

        pasarela = pasarela_para(comando.medio, self.configuracion_pasarela)
        pago = self._apartar(reserva, comando.medio, pasarela.nombre)

        try:
            resultado = pasarela.cobrar(
                monto=a_dinero(pago.monto),
                referencia_interna=f"reserva-{pago.reserva_id}",
            )
        except Exception:
            # Si la pasarela revienta se suelta el pago apartado, para que el
            # cliente pueda volver a intentar.
            db.session.delete(pago)
            db.session.commit()
            raise

        if not resultado.aprobado:
            self._registrar_rechazo(pago, resultado.motivo)
            raise PagoRechazado(
                resultado.motivo or "La pasarela rechazo el pago.",
                reserva_id=pago.reserva_id,
            )

        pago.estado = Pago.APROBADO
        pago.referencia_externa = resultado.referencia
        db.session.commit()

        return pago, self._confirmar_reserva(pago, comando.id_peticion)

    @staticmethod
    def _exigir_cobrable(reserva: dict) -> None:
        if reserva.get("estado") != "PENDIENTE":
            estado = _(ETIQUETAS_ESTADO.get(reserva.get("estado"), str(reserva.get("estado", "")))).lower()
            raise ReservaNoCobrable(
                _("La reserva #%(v0)s esta %(v1)s y no admite pago.") % {'v0': reserva.get('id'), 'v1': estado},
                estado_actual=reserva.get("estado"),
            )

    @staticmethod
    def _apartar(reserva: dict, medio: str, pasarela: str) -> Pago:
        # El pago se guarda ANTES de llamar a la pasarela. Si llegan dos
        # peticiones a la vez para la misma reserva, la segunda choca con el
        # unique de reserva_id y no se cobra dos veces.
        pago = Pago(
            reserva_id=reserva["id"],
            monto=a_dinero(reserva["total"]),
            medio=medio,
            pasarela=pasarela,
            estado=Pago.PENDIENTE,
        )
        db.session.add(pago)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ReservaYaPagada(reserva_id=reserva["id"]) from None
        return pago

    @staticmethod
    def _registrar_rechazo(pago: Pago, motivo: str) -> None:
        logger.warning(
            "Pago rechazado para reserva %s por %s: %s",
            pago.reserva_id,
            pago.pasarela,
            motivo,
        )
        pago.estado = Pago.RECHAZADO
        pago.motivo_rechazo = (motivo or "")[:200]
        db.session.commit()

    def _confirmar_reserva(self, pago: Pago, id_peticion: str) -> str:
        # En el monolito el pago y la confirmacion iban en el mismo
        # transaction.atomic(). Ahora son dos bases de datos, asi que si Django
        # falla aca la plata ya se cobro: el pago NO se borra, queda con
        # reserva_confirmada=False para conciliarlo.
        try:
            reserva = self.reservas.confirmar(pago.reserva_id, id_peticion)
        except ErrorDePagos as error:
            logger.error(
                "Pago %s aprobado pero la reserva %s no se confirmo: %s",
                pago.id,
                pago.reserva_id,
                error,
            )
            raise ReservaSinConfirmar(
                pago_id=pago.id, reserva_id=pago.reserva_id
            ) from error

        pago.reserva_confirmada = True
        db.session.commit()
        return reserva.get("estado", "CONFIRMADA")


class ConsultaPagosService:

    def __init__(self, reservas) -> None:
        self.reservas = reservas

    def detalle_de(
        self, pago_id: int, autorizacion: str, id_peticion: str = ""
    ) -> tuple[Pago, str]:
        pago = db.session.get(Pago, pago_id)
        if pago is None:
            raise PagoNoEncontrado(_("No existe el pago %(v0)s.") % {'v0': pago_id}, pago_id=pago_id)
        # Igual que en v1: si la reserva es de otro cliente, Django responde 403.
        reserva = self.reservas.obtener(pago.reserva_id, autorizacion, id_peticion)
        return pago, reserva["estado"]


class SaludService:

    NOMBRE = "casalista-pagos"
    VERSION = "2.0.0"

    def estado(self) -> tuple[dict, bool]:
        viva = self._base_de_datos_responde()
        reporte = {
            "servicio": self.NOMBRE,
            "version": self.VERSION,
            "base_de_datos": "ok" if viva else "sin-conexion",
        }
        return reporte, viva

    @staticmethod
    def _base_de_datos_responde() -> bool:
        try:
            db.session.execute(text("SELECT 1"))
            return True
        except Exception:
            db.session.rollback()
            return False
