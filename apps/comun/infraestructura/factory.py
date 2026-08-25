from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class FactoryPorEntorno:

    variable_de_entorno: str = ""
    valor_por_defecto: str = ""
    registro: dict = {}

    @classmethod
    def crear(cls, tipo: str | None = None):
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
