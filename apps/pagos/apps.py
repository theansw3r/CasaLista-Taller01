from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.apps import AppConfig


class PagosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pagos"
    label = "pagos"
    verbose_name = _lazy("CasaLista - Pagos")
