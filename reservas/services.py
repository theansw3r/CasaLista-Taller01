"""
Capa de aplicacion (Service Layer).

`ReservaService` es el unico que conoce el ALGORITMO del caso de uso "crear
reserva": buscar los datos, armar el objeto con el Builder y avisarle al
cliente. No conoce HTTP y no conoce implementaciones concretas: recibe sus
colaboradores por el constructor (Inyeccion de Dependencias) y, si no se los
dan, se los pide a las Factories.
"""

from .domain.excepciones import ClienteNoRegistrado, RecursoInexistente
from .domain.puertos import CalculadorTarifa, Notificador
from .domain.reserva_builder import ReservaBuilder
from .dto import CrearReservaCommand
from .infra.factories import CalculadorTarifaFactory, NotificadorFactory
from .models import BloqueDisponibilidad, Cliente, Reserva, Servicio


class ReservaService:
    """Caso de uso: un cliente reserva una franja con un profesional."""

    def __init__(
        self,
        notificador: Notificador | None = None,
        calculador_tarifa: CalculadorTarifa | None = None,
        builder_factory=ReservaBuilder,
    ) -> None:
        # Los valores por defecto vienen de las Factories; en pruebas se
        # inyectan dobles sin tocar variables de entorno.
        self.notificador = notificador or NotificadorFactory.crear()
        self.calculador_tarifa = calculador_tarifa or CalculadorTarifaFactory.crear()
        self.nuevo_builder = builder_factory

    # ------------------------------------------------------------------
    def crear_reserva(self, comando: CrearReservaCommand) -> Reserva:
        """Orquesta el flujo. Las reglas se validan dentro del Builder."""
        cliente = self._obtener_cliente(comando.usuario_id)
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

    # ------------------------------------------------------------------
    # Consultas de apoyo: traducen "no existe" al lenguaje del dominio.
    # ------------------------------------------------------------------
    @staticmethod
    def _obtener_cliente(usuario_id: int) -> Cliente:
        try:
            return Cliente.objects.select_related("usuario").get(usuario_id=usuario_id)
        except Cliente.DoesNotExist:
            raise ClienteNoRegistrado(
                "La cuenta autenticada no tiene un perfil de cliente."
            ) from None

    @staticmethod
    def _obtener_bloque(bloque_id: int) -> BloqueDisponibilidad:
        try:
            return BloqueDisponibilidad.objects.select_related("profesional").get(
                pk=bloque_id
            )
        except BloqueDisponibilidad.DoesNotExist:
            raise RecursoInexistente(
                f"No existe el bloque de agenda {bloque_id}."
            ) from None

    @staticmethod
    def _obtener_servicio(servicio_id: int) -> Servicio:
        try:
            return Servicio.objects.select_related("profesional").get(pk=servicio_id)
        except Servicio.DoesNotExist:
            raise RecursoInexistente(f"No existe el servicio {servicio_id}.") from None
