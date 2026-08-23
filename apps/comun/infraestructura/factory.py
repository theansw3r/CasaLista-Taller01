"""
Base compartida de las Factories del proyecto.

Las tres Factories de CasaLista (notificador, tarifa y pasarela de pago)
resuelven el mismo problema: "dame la implementacion que corresponde al
entorno, sin que yo sepa cual es". Escribir tres veces el mismo `if` habria
sido duplicacion, asi que el mecanismo se factoriza aqui y cada Factory
concreta solo declara TRES cosas: que variable lee, cual es su valor por
defecto y cual es su registro de implementaciones.

Sobre el registro como diccionario en vez de `if/elif`: agregar una variante
nueva es agregar una linea al registro, sin tocar el metodo `crear()`. Eso es
el Principio Abierto/Cerrado de forma literal: abierto a extension (nuevas
entradas), cerrado a modificacion (el algoritmo de seleccion no cambia).
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class FactoryPorEntorno:
    """Resuelve una variable de configuracion contra un registro de clases."""

    variable_de_entorno: str = ""
    valor_por_defecto: str = ""
    registro: dict = {}

    @classmethod
    def crear(cls, tipo: str | None = None):
        """Instancia la implementacion pedida, o la que dicte la configuracion.

        El argumento `tipo` existe para las pruebas y para casos en que el
        llamador necesita forzar una variante concreta (por ejemplo, cobrar
        con PSE aunque el entorno tenga TARJETA por defecto).
        """
        clave = (tipo or cls.configuracion_actual()).strip().upper()
        try:
            implementacion = cls.registro[clave]
        except KeyError:
            # Fallar aqui, al arrancar, es mucho mejor que fallar en mitad de
            # una reserva. Un valor mal escrito en el .env se detecta al
            # primer uso y con un mensaje que dice cuales eran las opciones.
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
