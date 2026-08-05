"""
Capa de interfaz.

Unica responsabilidad: tomar los datos del request, entregarselos al Service y
traducir el resultado a HTTP. No hay reglas de negocio ni consultas al ORM.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .domain.excepciones import ReglaDeNegocioViolada
from .forms import CrearReservaForm, datos_del_request
from .presenters import serializar_reserva
from .services import ReservaService


class CrearReservaView(LoginRequiredMixin, View):
    """POST /api/reservas/ -> crea una reserva en estado PENDIENTE."""

    servicio = ReservaService  # inyectable: as_view(servicio=OtroService)

    def post(self, request, *args, **kwargs):
        formulario = CrearReservaForm(datos_del_request(request))
        if not formulario.is_valid():
            return JsonResponse({"errores": formulario.errors}, status=400)
        try:
            reserva = self.servicio().crear_reserva(formulario.a_comando(request.user.pk))
        except ReglaDeNegocioViolada as error:
            return JsonResponse(error.como_respuesta(), status=error.estado_http)
        return JsonResponse(serializar_reserva(reserva), status=201)
