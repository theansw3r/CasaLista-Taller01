from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.catalogo.dominio.excepciones import ServicioNoEncontrado
from apps.catalogo.models import Servicio
from apps.comun.dominio.excepciones import AccesoNoAutorizado
from apps.cuentas.services import ConsultaPerfilService
from apps.reservas.dominio.agenda import ReglasAgenda
from apps.reservas.dominio.cancelacion import PoliticaDeCancelacionEstandar
from apps.reservas.dominio.ciclo_de_vida import CicloDeVidaReserva
from apps.reservas.dominio.excepciones import BloqueNoEncontrado, ReservaNoEncontrada
from apps.reservas.dominio.puertos import (
    CalculadorTarifa,
    Notificador,
    PoliticaDeCancelacion,
)
from apps.reservas.dominio.reserva_builder import ReservaBuilder
from apps.reservas.dto import (
    AbrirDisponibilidadCommand,
    CancelarReservaCommand,
    CrearReservaCommand,
)
from apps.reservas.infraestructura.factories import (
    CalculadorTarifaFactory,
    NotificadorFactory,
)
from apps.reservas.models import BloqueDisponibilidad, Reserva


class AgendaService:

    def abrir_disponibilidad(
        self, comando: AbrirDisponibilidadCommand
    ) -> BloqueDisponibilidad:
        profesional = ConsultaPerfilService.profesional_de(comando.usuario_id)

        ReglasAgenda.exigir_rango_valido(comando.inicio, comando.fin)
        ReglasAgenda.exigir_sin_solapamiento(profesional, comando.inicio, comando.fin)

        return BloqueDisponibilidad.objects.create(
            profesional=profesional,
            inicio=comando.inicio,
            fin=comando.fin,
            estado=BloqueDisponibilidad.Estado.LIBRE,
        )

    def bloques_libres(self, profesional_id: int, desde=None):
        momento = desde or timezone.now()
        return list(
            BloqueDisponibilidad.objects.filter(
                profesional_id=profesional_id,
                estado=BloqueDisponibilidad.Estado.LIBRE,
                inicio__gte=momento,
            ).select_related("profesional")
        )

    def mi_agenda(self, usuario_id: int):
        """Todas las franjas del profesional, libres y ocupadas.

        A diferencia de `bloques_libres`, que es la vitrina del cliente, esta
        es la vista de trabajo del profesional: necesita ver lo que ya le
        reservaron, no solo lo que sigue disponible.
        """
        profesional = ConsultaPerfilService.profesional_de(usuario_id)
        return list(
            BloqueDisponibilidad.objects.filter(
                profesional=profesional
            ).select_related("profesional")
        )

    def reservas_recibidas(self, usuario_id: int):
        """Reservas que le hicieron al profesional autenticado."""
        profesional = ConsultaPerfilService.profesional_de(usuario_id)
        return (
            Reserva.objects.filter(profesional=profesional)
            .select_related("cliente", "bloque", "profesional")
            .prefetch_related("detalles__servicio")
        )


class ReservaService:

    def __init__(
        self,
        notificador: Notificador | None = None,
        calculador_tarifa: CalculadorTarifa | None = None,
        builder_factory=ReservaBuilder,
    ) -> None:
        self.notificador = notificador or NotificadorFactory.crear()
        self.calculador_tarifa = calculador_tarifa or CalculadorTarifaFactory.crear()
        self.nuevo_builder = builder_factory

    @transaction.atomic
    def crear_reserva(self, comando: CrearReservaCommand) -> Reserva:
        cliente = ConsultaPerfilService.cliente_de(comando.usuario_id)
        bloque = self._obtener_bloque(comando.bloque_id)

        builder = (
            self.nuevo_builder()
            .para_cliente(cliente)
            .en_bloque(bloque)
            .en_direccion(comando.direccion, comando.zona)
            .con_calculador_tarifa(self.calculador_tarifa)
        )
        for linea in comando.lineas:
            builder.agregar_servicio(
                self._obtener_servicio(linea.servicio_id), linea.cantidad
            )

        reserva = builder.build()

        self.notificador.enviar_confirmacion_reserva(reserva)
        return reserva

    @staticmethod
    def _obtener_bloque(bloque_id: int) -> BloqueDisponibilidad:
        try:
            return BloqueDisponibilidad.objects.select_related("profesional").get(
                pk=bloque_id
            )
        except BloqueDisponibilidad.DoesNotExist:
            raise BloqueNoEncontrado(
                _("No existe la franja de agenda %(id)s.") % {"id": bloque_id}, bloque_id=bloque_id
            ) from None

    @staticmethod
    def _obtener_servicio(servicio_id: int) -> Servicio:
        try:
            return Servicio.objects.select_related("profesional").get(pk=servicio_id)
        except Servicio.DoesNotExist:
            raise ServicioNoEncontrado(
                _("No existe el servicio %(id)s.") % {"id": servicio_id}, servicio_id=servicio_id
            ) from None


class ConsultaReservasService:

    def reservas_de(self, usuario_id: int):
        cliente = ConsultaPerfilService.cliente_de(usuario_id)
        return (
            Reserva.objects.filter(cliente=cliente)
            .select_related("profesional", "bloque", "cliente")
            .prefetch_related("detalles__servicio")
        )

    def detalle_de(self, usuario_id: int, reserva_id: int) -> Reserva:
        reserva = self._obtener(reserva_id)
        cliente = ConsultaPerfilService.cliente_de(usuario_id)
        if reserva.cliente_id != cliente.pk:
            raise AccesoNoAutorizado(
                _("La reserva pertenece a otro cliente."), reserva_id=reserva_id
            )
        return reserva

    @staticmethod
    def _obtener(reserva_id: int) -> Reserva:
        try:
            return (
                Reserva.objects.select_related("profesional", "bloque", "cliente")
                .prefetch_related("detalles__servicio")
                .get(pk=reserva_id)
            )
        except Reserva.DoesNotExist:
            raise ReservaNoEncontrada(
                _("No existe la reserva %(id)s.") % {"id": reserva_id}, reserva_id=reserva_id
            ) from None


class ConfirmacionReservaService:
    """RN-03 desde afuera: la llama el microservicio de pagos cuando la
    pasarela aprueba. Antes esto pasaba dentro de PagoService."""

    def confirmar(self, reserva_id: int) -> Reserva:
        with transaction.atomic():
            try:
                reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
            except Reserva.DoesNotExist:
                raise ReservaNoEncontrada(
                    _("No existe la reserva %(id)s.") % {"id": reserva_id}, reserva_id=reserva_id
                ) from None
            CicloDeVidaReserva.confirmar(reserva)
            reserva.save(update_fields=["estado", "actualizada_en"])
        return reserva


class CancelacionReservaService:

    def __init__(
        self,
        politica: PoliticaDeCancelacion | None = None,
        consultas: ConsultaReservasService | None = None,
    ) -> None:
        self.politica = politica or PoliticaDeCancelacionEstandar()
        self.consultas = consultas or ConsultaReservasService()

    def cancelar(self, comando: CancelarReservaCommand) -> Reserva:
        reserva = self.consultas.detalle_de(comando.usuario_id, comando.reserva_id)

        CicloDeVidaReserva.cancelar(reserva)
        penalizacion = self.politica.calcular_penalizacion(reserva, timezone.now())

        with transaction.atomic():
            reserva.penalizacion = penalizacion
            reserva.save(update_fields=["estado", "penalizacion", "actualizada_en"])

            bloque = BloqueDisponibilidad.objects.select_for_update().get(
                pk=reserva.bloque_id
            )
            ReglasAgenda.liberar(bloque)
            bloque.save(update_fields=["estado"])

        return reserva
