from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.contrib.auth.models import AbstractBaseUser

from reservas.domain.exceptions import (
    BloqueNoDisponible,
    DatosReservaInvalidos,
    ProfesionalNoValido,
    ServiciosInvalidos,
)
from reservas.models import BloqueDisponibilidad, DetalleReserva, Reserva, Servicio


@dataclass(frozen=True)
class ReservaConstruida:
    reserva: Reserva
    detalles: list[DetalleReserva]


class ReservaBuilder:
    # Construye una reserva válida sin persistirla.

    def __init__(self) -> None:
        self._cliente: AbstractBaseUser | None = None
        self._bloque: BloqueDisponibilidad | None = None
        self._items: list[tuple[Servicio, int]] = []

    def para_cliente(self, cliente: AbstractBaseUser) -> "ReservaBuilder":
        self._cliente = cliente
        return self

    def en_bloque(self, bloque: BloqueDisponibilidad) -> "ReservaBuilder":
        self._bloque = bloque
        return self

    def con_servicios(
        self,
        items: Iterable[tuple[Servicio, int]],
    ) -> "ReservaBuilder":
        self._items = list(items)
        return self

    def build(self) -> ReservaConstruida:
        self._validar_datos_basicos()
        assert self._cliente is not None
        assert self._bloque is not None

        total = Decimal("0")
        detalles: list[DetalleReserva] = []

        for servicio, cantidad in self._items:
            self._validar_item(servicio, cantidad)
            subtotal = servicio.precio_base * cantidad
            total += subtotal
            detalles.append(
                DetalleReserva(
                    servicio=servicio,
                    cantidad=cantidad,
                    precio_unitario=servicio.precio_base,
                )
            )

        reserva = Reserva(
            cliente=self._cliente,
            profesional=self._bloque.profesional,
            bloque=self._bloque,
            estado=Reserva.Estado.PENDIENTE,
            total=total,
        )
        reserva.full_clean(exclude=["id"])

        for detalle in detalles:
            detalle.reserva = reserva
            detalle.clean()

        return ReservaConstruida(reserva=reserva, detalles=detalles)

    def _validar_datos_basicos(self) -> None:
        if self._cliente is None or not getattr(self._cliente, "pk", None):
            raise DatosReservaInvalidos("El cliente debe estar autenticado.")
        if self._bloque is None:
            raise DatosReservaInvalidos("Debe seleccionar un bloque.")
        if not self._bloque.esta_libre():
            raise BloqueNoDisponible("El bloque seleccionado ya no está disponible.")
        if not self._bloque.profesional.verificado:
            raise ProfesionalNoValido("El profesional aún no está verificado.")
        if not self._items:
            raise ServiciosInvalidos("Debe seleccionar al menos un servicio.")

    def _validar_item(self, servicio: Servicio, cantidad: int) -> None:
        assert self._bloque is not None
        if not servicio.activo:
            raise ServiciosInvalidos(f"El servicio '{servicio.nombre}' está inactivo.")
        if servicio.profesional_id != self._bloque.profesional_id:
            raise ServiciosInvalidos(
                "Todos los servicios deben pertenecer al profesional del bloque."
            )
        if cantidad <= 0:
            raise ServiciosInvalidos("La cantidad debe ser mayor que cero.")
