"""
Paginas HTML de lectura.

Se separan de `views.py` a proposito: `views.py` es la capa de interfaz del
caso de uso refactorizado (Crear Reserva, con Service + Builder). Estas
vistas son solo lectura y no tienen reglas de negocio que orquestar.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from .models import Reserva


class InicioView(TemplateView):
    template_name = "index.html"


class MisReservasListView(LoginRequiredMixin, ListView):
    """Lista las reservas del cliente autenticado."""

    model = Reserva
    template_name = "reservas/mis_reservas.html"
    context_object_name = "reservas"

    def get_queryset(self):
        cliente = getattr(self.request.user, "cliente", None)
        if cliente is None:
            return Reserva.objects.none()
        return Reserva.objects.filter(cliente=cliente).select_related(
            "profesional", "bloque"
        )
