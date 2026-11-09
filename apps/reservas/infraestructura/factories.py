from apps.comun.infraestructura.factory import FactoryPorEntorno
from apps.reservas.dominio.puertos import CalculadorTarifa, Notificador
from apps.reservas.dominio.tarifas import TarifaBase, TarifaDinamica
from apps.reservas.infraestructura.notificaciones import (
    NotificadorConsola,
    NotificadorAsincrono,
    NotificadorEmail,
)


class NotificadorFactory(FactoryPorEntorno):

    variable_de_entorno = "NOTIFICADOR_TYPE"
    valor_por_defecto = "MOCK"
    registro = {
        "ASYNC": NotificadorAsincrono,
        "MOCK": NotificadorConsola,
        "REAL": NotificadorEmail,
    }

    @classmethod
    def crear(cls, tipo: str | None = None) -> Notificador:
        return super().crear(tipo)


class CalculadorTarifaFactory(FactoryPorEntorno):

    variable_de_entorno = "TARIFA_TYPE"
    valor_por_defecto = "BASE"
    registro = {
        "BASE": TarifaBase,
        "DINAMICA": TarifaDinamica,
    }

    @classmethod
    def crear(cls, tipo: str | None = None) -> CalculadorTarifa:
        return super().crear(tipo)
