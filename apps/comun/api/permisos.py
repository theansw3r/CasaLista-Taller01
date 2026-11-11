import hmac

from django.conf import settings
from django.utils.translation import gettext_lazy as _lazy
from rest_framework.permissions import BasePermission

CABECERA_TOKEN = "HTTP_X_TOKEN_SERVICIO"


class EsServicioInterno(BasePermission):
    """Deja pasar solo a otros servicios de CasaLista (hoy, pagos en Flask).

    No sirve el JWT del cliente: con el, un cliente podria confirmarse la
    reserva sin haber pagado.
    """

    message = _lazy("Esta ruta solo la pueden usar los servicios internos de CasaLista.")

    def has_permission(self, request, view) -> bool:
        esperado = settings.TOKEN_SERVICIO_PAGOS
        recibido = request.META.get(CABECERA_TOKEN, "")
        return bool(esperado) and hmac.compare_digest(recibido, esperado)
