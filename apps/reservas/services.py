"""
Capa de aplicacion del modulo Agenda y Reservas.

Hay una clase por flujo de negocio y ninguna hace dos cosas (SRP):

    AgendaService             el profesional publica y consulta franjas
    ReservaService            el cliente crea una reserva
    ConsultaReservasService   el cliente lee sus reservas
    CancelacionReservaService el cliente cancela y se calcula RN-04

Se separaron a proposito en lugar de escribir un unico `ReservaService` con
seis metodos: crear y cancelar cambian por razones distintas (una depende de
la tarifa, la otra de la politica de cancelacion) y tienen colaboradores
distintos. Un solo servicio habria acabado dependiendo de todo.

Lo que un servicio SI hace: resolver ids a entidades, orquestar los pasos del
caso de uso y controlar la transaccion cuando escribe en varias tablas.
Lo que un servicio NO hace: validar reglas (eso es del dominio), conocer HTTP
ni instanciar implementaciones concretas (eso es de las Factories).
"""

from django.db import transaction
from django.utils import timezone

from apps.catalogo.dominio.excepciones import ServicioNoEncontrado
from apps.catalogo.models import Servicio
from apps.cuentas.services import ConsultaPerfilService
from apps.comun.dominio.excepciones import AccesoNoAutorizado
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
    """Caso de uso: un profesional gestiona su disponibilidad."""

    def abrir_disponibilidad(
        self, comando: AbrirDisponibilidadCommand
    ) -> BloqueDisponibilidad:
        """Publica una franja nueva. 409 si se pisa con otra ya publicada."""
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
        """Franjas que un cliente todavia puede reservar.

        Se descartan las que ya pasaron: mostrar un horario de ayer solo
        genera un 409 despues.
        """
        momento = desde or timezone.now()
        return list(
            BloqueDisponibilidad.objects.filter(
                profesional_id=profesional_id,
                estado=BloqueDisponibilidad.Estado.LIBRE,
                inicio__gte=momento,
            ).select_related("profesional")
        )


class ReservaService:
    """Caso de uso: un cliente reserva una franja con un profesional.

    Es el flujo mas complejo del sistema y el que justifica toda la
    arquitectura. El servicio conoce el ALGORITMO (que pasos y en que orden),
    el Builder conoce las REGLAS y las Factories conocen las
    IMPLEMENTACIONES. Ninguno de los tres invade al otro.
    """

    def __init__(
        self,
        notificador: Notificador | None = None,
        calculador_tarifa: CalculadorTarifa | None = None,
        builder_factory=ReservaBuilder,
    ) -> None:
        # Inyeccion de dependencias con valor por defecto: en produccion los
        # colaboradores los elige la Factory segun el entorno; en las pruebas
        # se pasan dobles por el constructor, sin tocar variables de entorno.
        self.notificador = notificador or NotificadorFactory.crear()
        self.calculador_tarifa = calculador_tarifa or CalculadorTarifaFactory.crear()
        self.nuevo_builder = builder_factory

    def crear_reserva(self, comando: CrearReservaCommand) -> Reserva:
        """Orquesta el flujo. Las reglas se validan dentro del Builder."""
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

        # La notificacion va DESPUES de que el Builder cerro su transaccion.
        # Si fuera dentro, un correo lento retrasaria el commit y mantendria
        # el bloqueo del bloque abierto mas tiempo del necesario.
        self.notificador.enviar_confirmacion_reserva(reserva)
        return reserva

    # ------------------------------------------------------------------
    # Traduccion de ids a entidades. Es la frontera con el ORM: de aqui hacia
    # arriba nadie vuelve a ver un DoesNotExist de Django.
    # ------------------------------------------------------------------
    @staticmethod
    def _obtener_bloque(bloque_id: int) -> BloqueDisponibilidad:
        try:
            return BloqueDisponibilidad.objects.select_related("profesional").get(
                pk=bloque_id
            )
        except BloqueDisponibilidad.DoesNotExist:
            raise BloqueNoEncontrado(
                f"No existe la franja de agenda {bloque_id}.", bloque_id=bloque_id
            ) from None

    @staticmethod
    def _obtener_servicio(servicio_id: int) -> Servicio:
        try:
            return Servicio.objects.select_related("profesional").get(pk=servicio_id)
        except Servicio.DoesNotExist:
            raise ServicioNoEncontrado(
                f"No existe el servicio {servicio_id}.", servicio_id=servicio_id
            ) from None


class ConsultaReservasService:
    """Caso de uso de lectura: el cliente revisa sus reservas."""

    def reservas_de(self, usuario_id: int):
        cliente = ConsultaPerfilService.cliente_de(usuario_id)
        return (
            Reserva.objects.filter(cliente=cliente)
            .select_related("profesional", "bloque", "cliente")
            .prefetch_related("detalles__servicio")
        )

    def detalle_de(self, usuario_id: int, reserva_id: int) -> Reserva:
        """Una reserva concreta, siempre que sea del cliente que pregunta.

        La comprobacion de propiedad esta aqui y no en la vista: es una regla
        (una reserva es privada de su cliente), no una preocupacion de HTTP.
        """
        reserva = self._obtener(reserva_id)
        cliente = ConsultaPerfilService.cliente_de(usuario_id)
        if reserva.cliente_id != cliente.pk:
            raise AccesoNoAutorizado(
                "La reserva pertenece a otro cliente.", reserva_id=reserva_id
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
                f"No existe la reserva {reserva_id}.", reserva_id=reserva_id
            ) from None


class CancelacionReservaService:
    """Caso de uso: el cliente cancela una reserva (RN-01 y RN-04).

    Recibe la politica de cancelacion por constructor. Cuando exista una
    politica distinta (por ejemplo, sin penalizacion para clientes
    frecuentes), se inyecta otra clase que cumpla el mismo puerto y este
    servicio no cambia.
    """

    def __init__(
        self,
        politica: PoliticaDeCancelacion | None = None,
        consultas: ConsultaReservasService | None = None,
    ) -> None:
        self.politica = politica or PoliticaDeCancelacionEstandar()
        self.consultas = consultas or ConsultaReservasService()

    def cancelar(self, comando: CancelarReservaCommand) -> Reserva:
        reserva = self.consultas.detalle_de(comando.usuario_id, comando.reserva_id)

        # El estado se decide antes de abrir la transaccion: si la reserva ya
        # estaba cancelada, no tiene sentido bloquear filas para nada.
        CicloDeVidaReserva.cancelar(reserva)
        penalizacion = self.politica.calcular_penalizacion(reserva, timezone.now())

        # Cancelar la reserva y liberar la franja son un solo hecho del
        # negocio (RN-01). Si se guardara la cancelacion y fallara la
        # liberacion, la franja quedaria bloqueada para siempre.
        with transaction.atomic():
            reserva.penalizacion = penalizacion
            reserva.save(update_fields=["estado", "penalizacion", "actualizada_en"])

            bloque = BloqueDisponibilidad.objects.select_for_update().get(
                pk=reserva.bloque_id
            )
            ReglasAgenda.liberar(bloque)
            bloque.save(update_fields=["estado"])

        return reserva
