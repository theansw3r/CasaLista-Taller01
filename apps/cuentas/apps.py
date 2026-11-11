from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class CuentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cuentas"
    label = "cuentas"
    verbose_name = _lazy("CasaLista - Cuentas")
