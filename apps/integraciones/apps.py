from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class IntegracionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integraciones"
    label = "integraciones"
    verbose_name = _lazy("CasaLista - Integraciones")
