from __future__ import annotations

from django.db import transaction

from apps.catalogo.dominio.precios import CalculadoraDeServicio
from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.reservas.dominio.agenda import ReglasAgenda
from apps.reservas.dominio.excepciones import (
    BloqueDeOtroProfesional,
    CantidadInvalida,
    DatosDeReservaIncompletos,
    DuracionExcedeBloque,
    ReservaSinServicios,
    ServiciosDeDistintosProfesionales,
)
from apps.reservas.dominio.precios import CalculadoraDeReserva
from apps.reservas.dominio.puertos import CalculadorTarifa
from apps.reservas.dominio.tarifas import TarifaBase
from apps.reservas.models import BloqueDisponibilidad, DetalleReserva, Reserva


class ReservaBuilder:

    def __init__(self) -> None:
        self._cliente = None
        self._bloque = None
        self._direccion = ""
        self._zona = ""
        self._lineas: list[tuple] = []
        self._calculador: CalculadorTarifa = TarifaBase()

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

    def build(self) -> Reserva:
        self._validar()
        detalles = self._construir_detalles()

        with transaction.atomic():
            self._bloque = BloqueDisponibilidad.objects.select_for_update().get(
                pk=self._bloque.pk
            )
            ReglasAgenda.exigir_disponible(self._bloque)

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
            reserva.save()

            for detalle in detalles:
                detalle.reserva = reserva
            DetalleReserva.objects.bulk_create(detalles)

            ReglasAgenda.ocupar(self._bloque)
            self._bloque.save(update_fields=["estado"])

        return reserva

    def _validar(self) -> None:
        self._validar_datos_minimos()
        self._validar_lineas()
        self._validar_mismo_profesional()
        self._validar_profesional_habilitado()
        self._validar_coherencia_del_bloque()
        ReglasAgenda.exigir_disponible(self._bloque)
        self._validar_duracion()

    def _validar_datos_minimos(self) -> None:
        if self._cliente is None:
            raise DatosDeReservaIncompletos("Falta indicar el cliente de la reserva.")
        if self._bloque is None:
            raise DatosDeReservaIncompletos("Falta indicar la franja de agenda.")
        if not self._direccion or not self._zona:
            raise DatosDeReservaIncompletos(
                "Falta la direccion o la zona de la visita."
            )

    def _validar_lineas(self) -> None:
        if not self._lineas:
            raise ReservaSinServicios()
        for servicio, cantidad in self._lineas:
            if cantidad <= 0:
                raise CantidadInvalida(
                    f"La cantidad de '{servicio.nombre}' debe ser mayor que cero.",
                    servicio_id=servicio.pk,
                )
            CalculadoraDeServicio.exigir_disponible(servicio)

    def _validar_mismo_profesional(self) -> None:
        profesionales = {servicio.profesional_id for servicio, _ in self._lineas}
        if len(profesionales) > 1:
            raise ServiciosDeDistintosProfesionales(
                profesionales_recibidos=sorted(profesionales)
            )

    def _validar_profesional_habilitado(self) -> None:
        PoliticaDeCobertura.exigir_habilitado(self._profesional, self._zona)

    def _validar_coherencia_del_bloque(self) -> None:
        if self._bloque.profesional_id != self._profesional.id:
            raise BloqueDeOtroProfesional(
                "La franja elegida pertenece a otro profesional.",
                bloque_id=self._bloque.pk,
            )

    def _validar_duracion(self) -> None:
        solicitada = sum(
            CalculadoraDeServicio.duracion(servicio, cantidad)
            for servicio, cantidad in self._lineas
        )
        disponible = ReglasAgenda.duracion_minutos(self._bloque)
        if solicitada > disponible:
            raise DuracionExcedeBloque(
                f"Los servicios requieren {solicitada} minutos y la franja "
                f"solo tiene {disponible}.",
                minutos_solicitados=solicitada,
                minutos_disponibles=disponible,
            )

    @property
    def _profesional(self):
        return self._lineas[0][0].profesional

    def _construir_detalles(self) -> list[DetalleReserva]:
        return [
            DetalleReserva(
                servicio=servicio,
                cantidad=cantidad,
                precio_unitario=servicio.precio_base,
                duracion_unitaria_minutos=servicio.duracion_minutos,
            )
            for servicio, cantidad in self._lineas
        ]

    def previsualizar_total(self):
        self._validar_lineas()
        detalles = self._construir_detalles()
        if self._bloque is None:
            return CalculadoraDeReserva.suma_de_lineas(detalles)
        return self._calculador.calcular(detalles, self._bloque)
