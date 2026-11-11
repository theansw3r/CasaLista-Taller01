from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class PagosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pagos"
    label = "pagos"
    verbose_name = _lazy("CasaLista - Pagos")
