from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class ReservasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reservas"
    label = "reservas"
    verbose_name = _lazy("CasaLista - Reservas")
