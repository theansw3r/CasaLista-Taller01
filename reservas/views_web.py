"""
Paginas HTML.

Se separan de `views.py` a proposito: `views.py` es la capa de interfaz del
endpoint JSON del caso de uso refactorizado. Aqui viven las paginas para
navegador: leer datos (Inicio, Catalogo, MisReservas) y una interfaz alterna
al mismo caso de uso (CrearReservaWebView), que reutiliza el mismo
ReservaService.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormView

from .domain.excepciones import ReglaDeNegocioViolada
from .forms_web import CrearReservaWebForm
from .models import Reserva, Servicio
from .services import ReservaService


class InicioView(TemplateView):
    template_name = "index.html"


class CatalogoView(LoginRequiredMixin, ListView):
    """Paso 1: elegir que servicio se quiere contratar."""

    template_name = "reservas/catalogo.html"
    context_object_name = "servicios"

    def get_queryset(self):
        return (
            Servicio.objects.filter(activo=True, profesional__verificado=True)
            .select_related("profesional")
            .order_by("profesional__nombre", "nombre")
        )


class CrearReservaWebView(LoginRequiredMixin, FormView):
    """Paso 2: elegir horario y direccion. Mismo Service que la API."""

    template_name = "reservas/crear_reserva.html"
    form_class = CrearReservaWebForm
    success_url = reverse_lazy("portal:mis-reservas")
    servicio_de_aplicacion = ReservaService  # inyectable en pruebas

    @cached_property
    def servicio_elegido(self) -> Servicio:
        return get_object_or_404(
            Servicio.objects.select_related("profesional"),
            pk=self.kwargs["servicio_id"],
            activo=True,
            profesional__verificado=True,
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "servicio": self.servicio_elegido}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["servicio"] = self.servicio_elegido
        contexto["profesional"] = self.servicio_elegido.profesional
        return contexto

    def form_valid(self, form):
        try:
            reserva = self.servicio_de_aplicacion().crear_reserva(
                form.a_comando(self.request.user.pk)
            )
        except ReglaDeNegocioViolada as error:
            form.add_error(None, f"[{error.codigo}] {error}")
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Reserva #{reserva.pk} creada por $ {reserva.total} "
            f"(tarifa {reserva.tarifa_aplicada}). Queda pendiente de pago.",
        )
        return super().form_valid(form)


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
