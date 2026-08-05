"""
Paginas HTML.

Se separan de `views.py` a proposito: `views.py` es la capa de interfaz del
endpoint JSON del caso de uso refactorizado. Aqui viven las paginas para
navegador: leer datos (Inicio, MisReservas) y una interfaz alterna al mismo
caso de uso (CrearReservaWebView), que reutiliza el mismo ReservaService.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormView

from .domain.excepciones import ReglaDeNegocioViolada
from .forms_web import CrearReservaWebForm
from .models import Reserva
from .services import ReservaService


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


class CrearReservaWebView(LoginRequiredMixin, FormView):
    """Version HTML de crear una reserva: mismo Service, mismo Builder."""

    template_name = "reservas/crear_reserva.html"
    form_class = CrearReservaWebForm
    success_url = reverse_lazy("portal:mis-reservas")
    servicio = ReservaService  # inyectable, igual que CrearReservaView

    def form_valid(self, form):
        try:
            self.servicio().crear_reserva(form.a_comando(self.request.user.pk))
        except ReglaDeNegocioViolada as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, "Reserva creada. Queda pendiente de pago.")
        return super().form_valid(form)
