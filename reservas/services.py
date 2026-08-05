from collections.abc import Mapping
from typing import Any

from django.db import IntegrityError, transaction

from reservas.domain.builders import ReservaBuilder
from reservas.domain.exceptions import (
    BloqueNoDisponible,
    DatosReservaInvalidos,
    ServiciosInvalidos,
)
from reservas.infra.factories import NotificadorFactory
from reservas.infra.notifiers import NotificadorReserva
from reservas.models import (
    BloqueDisponibilidad,
    DetalleReserva,
    Reserva,
    Servicio,
)


class ReservaService:
    # Orquesta el caso de uso sin mezclar HTTP ni detalles de presentación.

    def __init__(self, notificador: NotificadorReserva | None = None) -> None:
        self.notificador = notificador or NotificadorFactory.crear()

    def crear_reserva(
        self,
        *,
        cliente: Any,
        datos: Mapping[str, Any],
    ) -> Reserva:
        try:
            with transaction.atomic():
                return self._crear_en_transaccion(cliente=cliente, datos=datos)
        except IntegrityError as error:
            raise BloqueNoDisponible(
                "El bloque fue ocupado por otra reserva."
            ) from error

    def _crear_en_transaccion(
        self,
        *,
        cliente: Any,
        datos: Mapping[str, Any],
    ) -> Reserva:
        bloque = self._obtener_bloque_bloqueado(datos)
        items = self._obtener_items(datos)

        construida = (
            ReservaBuilder()
            .para_cliente(cliente)
            .en_bloque(bloque)
            .con_servicios(items)
            .build()
        )

        construida.reserva.save()
        DetalleReserva.objects.bulk_create(construida.detalles)

        bloque.ocupar()
        bloque.save(update_fields=["estado"])

        transaction.on_commit(
            lambda: self.notificador.enviar_reserva_creada(construida.reserva)
        )
        return construida.reserva

    @staticmethod
    def _obtener_bloque_bloqueado(
        datos: Mapping[str, Any],
    ) -> BloqueDisponibilidad:
        try:
            bloque_id = int(datos["bloque_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise DatosReservaInvalidos("bloque_id es obligatorio.") from error

        try:
            return (
                BloqueDisponibilidad.objects.select_for_update()
                .select_related("profesional")
                .get(pk=bloque_id)
            )
        except BloqueDisponibilidad.DoesNotExist as error:
            raise DatosReservaInvalidos("El bloque no existe.") from error

    @staticmethod
    def _obtener_items(
        datos: Mapping[str, Any],
    ) -> list[tuple[Servicio, int]]:
        items_crudos = datos.get("servicios")
        if not isinstance(items_crudos, list) or not items_crudos:
            raise ServiciosInvalidos(
                "servicios debe ser una lista con al menos un elemento."
            )

        normalizados: list[tuple[int, int]] = []
        for item in items_crudos:
            try:
                servicio_id = int(item["servicio_id"])
                cantidad = int(item.get("cantidad", 1))
            except (KeyError, TypeError, ValueError) as error:
                raise ServiciosInvalidos(
                    "Cada servicio requiere servicio_id y una cantidad válida."
                ) from error
            normalizados.append((servicio_id, cantidad))

        ids = [servicio_id for servicio_id, _ in normalizados]
        if len(ids) != len(set(ids)):
            raise ServiciosInvalidos(
                "Un mismo servicio no debe aparecer repetido."
            )

        servicios = Servicio.objects.select_related("profesional").in_bulk(ids)
        if len(servicios) != len(ids):
            raise ServiciosInvalidos("Uno o más servicios no existen.")

        return [
            (servicios[servicio_id], cantidad)
            for servicio_id, cantidad in normalizados
        ]
