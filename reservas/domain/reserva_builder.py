"""
Patron Builder aplicado a la creacion de una Reserva.

Una Reserva no es un objeto plano: nace con lineas de detalle, con un total
calculado por una estrategia y ocupando un bloque de agenda. Construirla con
`Reserva.objects.create(...)` obliga a que quien llama recuerde el orden y las
validaciones. El Builder invierte eso: acumula la intencion paso a paso y solo
al final, en `build()`, decide si el objeto puede existir.

Contrato del Builder
--------------------
1. Los metodos `para_cliente`, `en_bloque`, `en_direccion`, `agregar_servicio`
   y `con_calculador_tarifa` devuelven `self` (Fluent Interface) y NO validan
   nada por si solos: el orden en que se llamen es indiferente.
2. `build()` valida TODAS las invariantes antes de tocar la base de datos.
   Si alguna falla lanza una excepcion de dominio y no se guarda nada.
3. La escritura ocurre dentro de una transaccion, y la disponibilidad del
   bloque se vuelve a verificar bajo bloqueo para sostener el atributo de
   calidad "consistencia de la agenda".
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import BloqueDisponibilidad, DetalleReserva, Reserva
from .excepciones import (
    BloqueDeOtroProfesional,
    BloqueNoDisponible,
    CantidadInvalida,
    DatosIncompletos,
    DuracionExcedeBloque,
    ProfesionalNoHabilitado,
    ReservaSinServicios,
    ServicioInactivo,
    ServiciosDeDistintosProfesionales,
)
from .puertos import CalculadorTarifa
from .tarifas import TarifaBase


class ReservaBuilder:
    """Construye una Reserva valida paso a paso."""

    def __init__(self) -> None:
        self._cliente = None
        self._bloque = None
        self._direccion = ""
        self._zona = ""
        self._lineas: list[tuple] = []
        self._calculador: CalculadorTarifa = TarifaBase()

    # ------------------------------------------------------------------
    # Interfaz fluida
    # ------------------------------------------------------------------
    def para_cliente(self, cliente) -> ReservaBuilder:
        self._cliente = cliente
        return self

    def en_bloque(self, bloque) -> ReservaBuilder:
        self._bloque = bloque
        return self

    def en_direccion(self, direccion: str, zona: str) -> ReservaBuilder:
        self._direccion = (direccion or "").strip()
        self._zona = (zona or "").strip()
        return self

    def agregar_servicio(self, servicio, cantidad: int = 1) -> ReservaBuilder:
        self._lineas.append((servicio, int(cantidad)))
        return self

    def con_calculador_tarifa(self, calculador: CalculadorTarifa) -> ReservaBuilder:
        self._calculador = calculador
        return self

    # ------------------------------------------------------------------
    # Construccion
    # ------------------------------------------------------------------
    def build(self) -> Reserva:
        """Valida y persiste la reserva. Devuelve la raiz del agregado."""
        self._validar()
        detalles = self._construir_detalles()

        with transaction.atomic():
            # Se relee el bloque bajo bloqueo: entre la validacion y el guardado
            # otro cliente pudo haber tomado la misma franja (RN-01).
            self._bloque = BloqueDisponibilidad.objects.select_for_update().get(
                pk=self._bloque.pk
            )
            self._validar_disponibilidad_del_bloque()

            reserva = Reserva(
                cliente=self._cliente,
                profesional=self._profesional,
                bloque=self._bloque,
                direccion=self._direccion,
                zona=self._zona,
                estado=Reserva.Estado.PENDIENTE,
                total=self._calculador.calcular(detalles, self._bloque),
                tarifa_aplicada=self._calculador.nombre,
            )
            self._asegurar_integridad_del_modelo(reserva)
            reserva.save()

            for detalle in detalles:
                detalle.reserva = reserva
            DetalleReserva.objects.bulk_create(detalles)

            self._bloque.ocupar()
            self._bloque.save(update_fields=["estado"])

        return reserva

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def _validar(self) -> None:
        self._validar_datos_minimos()
        self._validar_lineas()
        self._validar_mismo_profesional()          # RN-02
        self._validar_profesional_habilitado()     # RN-07
        self._validar_coherencia_del_bloque()      # RN-01
        self._validar_disponibilidad_del_bloque()  # RN-01
        self._validar_duracion()                   # RN-08

    def _validar_datos_minimos(self) -> None:
        if self._cliente is None:
            raise DatosIncompletos("Falta indicar el cliente de la reserva.")
        if self._bloque is None:
            raise DatosIncompletos("Falta indicar el bloque de agenda.")
        if not self._direccion or not self._zona:
            raise DatosIncompletos("Falta la direccion o la zona de la visita.")

    def _validar_lineas(self) -> None:
        if not self._lineas:
            raise ReservaSinServicios("La reserva debe incluir al menos un servicio.")
        for servicio, cantidad in self._lineas:
            if cantidad <= 0:
                raise CantidadInvalida(
                    f"La cantidad de '{servicio.nombre}' debe ser mayor que cero."
                )
            if not servicio.activo:
                raise ServicioInactivo(
                    f"El servicio '{servicio.nombre}' no esta disponible."
                )

    def _validar_mismo_profesional(self) -> None:
        ids = {servicio.profesional_id for servicio, _ in self._lineas}
        if len(ids) > 1:
            raise ServiciosDeDistintosProfesionales(
                "Todos los servicios de una reserva deben ser del mismo profesional."
            )

    def _validar_profesional_habilitado(self) -> None:
        profesional = self._profesional
        if not profesional.verificado:
            raise ProfesionalNoHabilitado(
                f"El profesional {profesional.nombre} no esta verificado."
            )
        if not profesional.cubre_zona(self._zona):
            raise ProfesionalNoHabilitado(
                f"El profesional {profesional.nombre} no cubre la zona {self._zona}."
            )

    def _validar_coherencia_del_bloque(self) -> None:
        if self._bloque.profesional_id != self._profesional.id:
            raise BloqueDeOtroProfesional(
                "El bloque de agenda pertenece a otro profesional."
            )

    def _validar_disponibilidad_del_bloque(self) -> None:
        if not self._bloque.esta_libre():
            raise BloqueNoDisponible("La franja horaria ya fue tomada.")
        ocupado = Reserva.objects.filter(
            bloque=self._bloque, estado__in=Reserva.ESTADOS_ACTIVOS
        ).exists()
        if ocupado:
            raise BloqueNoDisponible("La franja horaria ya tiene una reserva activa.")

    def _validar_duracion(self) -> None:
        solicitada = sum(
            servicio.duracion_minutos * cantidad for servicio, cantidad in self._lineas
        )
        disponible = self._bloque.duracion_minutos
        if solicitada > disponible:
            raise DuracionExcedeBloque(
                f"Los servicios requieren {solicitada} minutos y el bloque "
                f"solo tiene {disponible}."
            )

    @staticmethod
    def _asegurar_integridad_del_modelo(reserva: Reserva) -> None:
        """Ultima red de seguridad: el objeto es valido ANTES de `.save()`."""
        try:
            reserva.full_clean()
        except ValidationError as error:
            raise DatosIncompletos(
                f"La reserva construida no es valida: {error.messages}"
            ) from error

    # ------------------------------------------------------------------
    # Apoyo
    # ------------------------------------------------------------------
    @property
    def _profesional(self):
        return self._lineas[0][0].profesional

    def _construir_detalles(self) -> list[DetalleReserva]:
        """Lineas en memoria, con precio y duracion congelados (seccion 2.2)."""
        return [
            DetalleReserva(
                servicio=servicio,
                cantidad=cantidad,
                precio_unitario=servicio.precio_base,
                duracion_unitaria_minutos=servicio.duracion_minutos,
            )
            for servicio, cantidad in self._lineas
        ]
