"""
Patron Builder aplicado a la creacion de una Reserva.

Por que Reserva y no otra entidad
---------------------------------
Reserva es la entidad mas compleja del sistema: no nace sola. Para existir
necesita un cliente, una franja de agenda que hay que ocupar, una o varias
lineas de detalle con el precio congelado, un total calculado por una
estrategia intercambiable, y que se cumplan cinco reglas de negocio a la vez
(RN-01, RN-02, RN-07 y las derivadas de duracion y cantidad).

Con `Reserva.objects.create(...)` quien llama tendria que acordarse del orden,
de copiar los precios, de validar cada regla y de ocupar el bloque. El Builder
invierte eso: el llamador declara su intencion paso a paso y `build()` decide
si el objeto puede existir.

Contrato
--------
1. Los metodos `para_cliente`, `en_bloque`, `en_direccion`, `agregar_servicio`
   y `con_calculador_tarifa` devuelven `self` (interfaz fluida) y NO validan
   nada por si solos: el orden en que se llamen es indiferente.
2. `build()` valida TODAS las invariantes antes de tocar la base de datos. Si
   alguna falla, lanza una excepcion de dominio y no se guarda nada.
3. La escritura ocurre dentro de una transaccion y la disponibilidad del
   bloque se vuelve a verificar bajo bloqueo, para sostener el atributo de
   calidad "consistencia de la agenda".

Por que el Builder persiste y no el Service
-------------------------------------------
La reserva es un agregado: la reserva, sus detalles y el bloque ocupado se
guardan juntos o no se guarda ninguno. Quien conoce esa invariante es el
Builder, asi que es el quien abre la transaccion. Si la transaccion viviera en
el Service, la responsabilidad de "esto es atomico" quedaria separada de quien
sabe por que lo es.
"""

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
    """Construye una Reserva valida paso a paso."""

    def __init__(self) -> None:
        self._cliente = None
        self._bloque = None
        self._direccion = ""
        self._zona = ""
        self._lineas: list[tuple] = []
        # Tarifa por defecto para que el Builder sea usable sin configurar
        # nada (por ejemplo en una prueba). El Service inyecta la que dicte
        # el entorno.
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
        """Valida, persiste el agregado completo y devuelve su raiz."""
        self._validar()
        detalles = self._construir_detalles()

        with transaction.atomic():
            # Se relee el bloque bajo bloqueo. Entre la validacion de arriba y
            # este punto, otro cliente pudo haber tomado la misma franja: sin
            # este bloqueo, dos peticiones simultaneas venderian el mismo
            # horario dos veces (RN-01).
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

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def _validar(self) -> None:
        """Las invariantes, en el orden en que tiene sentido comprobarlas.

        Primero lo estructural (falta un dato), despues lo del catalogo, y al
        final lo que depende del estado de la agenda. Asi el mensaje de error
        que recibe el cliente es siempre el mas util: no tiene sentido decirle
        "la franja esta ocupada" si ni siquiera mando servicios.
        """
        self._validar_datos_minimos()
        self._validar_lineas()
        self._validar_mismo_profesional()  # RN-02
        self._validar_profesional_habilitado()  # RN-07
        self._validar_coherencia_del_bloque()  # RN-01
        ReglasAgenda.exigir_disponible(self._bloque)  # RN-01
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
            # Quien sabe si un servicio se puede vender es el catalogo, no la
            # reserva. El Builder pregunta, no reimplementa la regla.
            CalculadoraDeServicio.exigir_disponible(servicio)

    def _validar_mismo_profesional(self) -> None:
        """RN-02: una reserva involucra a un unico profesional."""
        profesionales = {servicio.profesional_id for servicio, _ in self._lineas}
        if len(profesionales) > 1:
            raise ServiciosDeDistintosProfesionales(
                profesionales_recibidos=sorted(profesionales)
            )

    def _validar_profesional_habilitado(self) -> None:
        """RN-07: delegada al modulo de Cuentas, que es su dueno."""
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

    # ------------------------------------------------------------------
    # Apoyo
    # ------------------------------------------------------------------
    @property
    def _profesional(self):
        """El profesional sale de los servicios, no se pide aparte.

        Como RN-02 exige que todos los servicios sean del mismo profesional,
        pedirlo como dato de entrada seria dar la oportunidad de que llegara
        uno distinto al de los servicios. Derivarlo elimina esa incoherencia
        por construccion.
        """
        return self._lineas[0][0].profesional

    def _construir_detalles(self) -> list[DetalleReserva]:
        """Lineas en memoria con precio y duracion congelados."""
        return [
            DetalleReserva(
                servicio=servicio,
                cantidad=cantidad,
                precio_unitario=servicio.precio_base,
                duracion_unitaria_minutos=servicio.duracion_minutos,
            )
            for servicio, cantidad in self._lineas
        ]

    # ------------------------------------------------------------------
    def previsualizar_total(self):
        """Total que tendria la reserva, sin guardar nada.

        Lo usa el front end para mostrar el precio antes de confirmar. Es el
        mismo calculo que hace `build()`, asi que el numero que ve el cliente
        y el que se cobra no se pueden separar.
        """
        self._validar_lineas()
        detalles = self._construir_detalles()
        if self._bloque is None:
            return CalculadoraDeReserva.suma_de_lineas(detalles)
        return self._calculador.calcular(detalles, self._bloque)
