"""
Factories del modulo de Reservas.

Resuelven dos ejes de variacion distintos, y por eso son dos clases y no una:

* `NotificadorFactory` -> una DEPENDENCIA EXTERNA (como sale el aviso).
* `CalculadorTarifaFactory` -> una VARIANTE DE LOGICA (cuanto se cobra).

Mezclarlas habria acoplado dos cosas que cambian por razones distintas: se
puede querer correo real con tarifa base, o consola con tarifa dinamica.

    NOTIFICADOR_TYPE=MOCK      ->  NotificadorConsola
    NOTIFICADOR_TYPE=REAL      ->  NotificadorEmail
    TARIFA_TYPE=BASE           ->  TarifaBase
    TARIFA_TYPE=DINAMICA       ->  TarifaDinamica

Quien pide un notificador (el Service) importa el puerto, no el adaptador:
nunca escribe `NotificadorEmail()` en su codigo.
"""

from apps.comun.infraestructura.factory import FactoryPorEntorno
from apps.reservas.dominio.puertos import CalculadorTarifa, Notificador
from apps.reservas.dominio.tarifas import TarifaBase, TarifaDinamica
from apps.reservas.infraestructura.notificaciones import (
    NotificadorConsola,
    NotificadorEmail,
)


class NotificadorFactory(FactoryPorEntorno):
    """Devuelve el Notificador que corresponde a NOTIFICADOR_TYPE."""

    variable_de_entorno = "NOTIFICADOR_TYPE"
    valor_por_defecto = "MOCK"
    registro = {
        "MOCK": NotificadorConsola,
        "REAL": NotificadorEmail,
    }

    @classmethod
    def crear(cls, tipo: str | None = None) -> Notificador:
        # Se reescribe solo para declarar el tipo de retorno: quien lee el
        # codigo ve que recibe un puerto, no una clase concreta.
        return super().crear(tipo)


class CalculadorTarifaFactory(FactoryPorEntorno):
    """Devuelve la estrategia de tarifa que corresponde a TARIFA_TYPE."""

    variable_de_entorno = "TARIFA_TYPE"
    valor_por_defecto = "BASE"
    registro = {
        "BASE": TarifaBase,
        "DINAMICA": TarifaDinamica,
    }

    @classmethod
    def crear(cls, tipo: str | None = None) -> CalculadorTarifa:
        return super().crear(tipo)
