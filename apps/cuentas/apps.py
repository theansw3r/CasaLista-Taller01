from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.apps import AppConfig


class CuentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cuentas"
    label = "cuentas"
    verbose_name = _lazy("CasaLista - Cuentas")
