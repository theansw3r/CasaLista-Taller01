from django.utils.translation import gettext as _, gettext_lazy as _lazy
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
                _("%(v0)s='%(v1)s' no es un valor valido. Opciones disponibles: %(v2)s.") % {'v0': cls.variable_de_entorno, 'v1': clave, 'v2': ', '.join(cls.opciones())}
            ) from None
        return implementacion()

    @classmethod
    def configuracion_actual(cls) -> str:
        return getattr(settings, cls.variable_de_entorno, cls.valor_por_defecto)

    @classmethod
    def opciones(cls) -> list[str]:
        return sorted(cls.registro)
