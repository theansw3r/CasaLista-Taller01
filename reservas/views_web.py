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
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormView

from .domain.excepciones import ReglaDeNegocioViolada
from .forms_web import CrearReservaWebForm
from .models import Reserva, Servicio
from .services import ReservaService


class ClienteRequeridoMixin(LoginRequiredMixin):
    """Exige sesion iniciada Y perfil de cliente.

    El Service ya rechaza a un usuario sin perfil (VAL-06), pero lo hace al
    final: el usuario llenaba el formulario entero para recibir el error.
    Aqui se adelanta la misma condicion para no hacerle perder el trabajo.
    Es una cortesia de la interfaz, no una regla nueva: la garantia sigue
    estando en el Service.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "cliente"):
            messages.warning(
                request,
                f"La cuenta '{request.user.username}' no tiene perfil de cliente, "
                f"asi que no puede reservar. Inicia sesion con una cuenta de "
                f"cliente o crea una en Registrarse.",
            )
            return redirect("portal:inicio")
        return super().dispatch(request, *args, **kwargs)


class InicioView(TemplateView):
    template_name = "index.html"


class CatalogoView(ClienteRequeridoMixin, ListView):
    """Paso 1: elegir que servicio se quiere contratar."""

    template_name = "reservas/catalogo.html"
    context_object_name = "servicios"

    def get_queryset(self):
        return (
            Servicio.objects.filter(activo=True, profesional__verificado=True)
            .select_related("profesional")
            .order_by("profesional__nombre", "nombre")
        )


class CrearReservaWebView(ClienteRequeridoMixin, FormView):
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


class MisReservasListView(ClienteRequeridoMixin, ListView):
    """Lista las reservas del cliente autenticado."""

    model = Reserva
    template_name = "reservas/mis_reservas.html"
    context_object_name = "reservas"

    def get_queryset(self):
        return Reserva.objects.filter(cliente=self.request.user.cliente).select_related(
            "profesional", "bloque"
        )
