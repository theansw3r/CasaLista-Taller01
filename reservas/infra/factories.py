"""
Patron Factory.

Quien necesita un notificador o un calculador de tarifa pide "el que
corresponda al entorno", no una clase concreta. Cambiar de comportamiento es
cambiar una variable de entorno, no editar codigo:

    NOTIFICADOR_TYPE=MOCK  ->  NotificadorConsola
    NOTIFICADOR_TYPE=REAL  ->  NotificadorEmail
    TARIFA_TYPE=BASE       ->  TarifaBase
    TARIFA_TYPE=DINAMICA   ->  TarifaDinamica

Agregar una tercera variante (por ejemplo NotificadorWhatsApp) es agregar una
entrada al registro: las Factories estan abiertas a extension y cerradas a
modificacion (Open/Closed).
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ..domain.puertos import CalculadorTarifa, Notificador
from ..domain.tarifas import TarifaBase, TarifaDinamica
from .notificaciones import NotificadorConsola, NotificadorEmail


class FactoryPorEntorno:
    """Resuelve una variable de entorno contra un registro de implementaciones."""

    variable_de_entorno: str = ""
    valor_por_defecto: str = ""
    registro: dict = {}

    @classmethod
    def crear(cls, tipo: str | None = None):
        """Instancia la implementacion pedida, o la que dicte el entorno."""
        clave = (tipo or cls.configuracion_actual()).strip().upper()
        try:
            implementacion = cls.registro[clave]
        except KeyError:
            raise ImproperlyConfigured(
                f"{cls.variable_de_entorno}='{clave}' no es un valor valido. "
                f"Opciones disponibles: {', '.join(cls.opciones())}."
            ) from None
        return implementacion()

    @classmethod
    def configuracion_actual(cls) -> str:
        return getattr(settings, cls.variable_de_entorno, cls.valor_por_defecto)

    @classmethod
    def opciones(cls) -> list[str]:
        return sorted(cls.registro)


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
