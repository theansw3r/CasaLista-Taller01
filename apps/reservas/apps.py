from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.apps import AppConfig


class ReservasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reservas"
    label = "reservas"
    verbose_name = _lazy("CasaLista - Reservas")
