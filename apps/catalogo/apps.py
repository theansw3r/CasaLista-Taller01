from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class CatalogoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalogo"
    label = "catalogo"
    verbose_name = _lazy("CasaLista - Catálogo")
