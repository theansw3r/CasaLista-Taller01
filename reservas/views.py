import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from reservas.domain.exceptions import ReservaError
from reservas.services import ReservaService


@method_decorator(login_required, name="dispatch")
class CrearReservaView(View):
    service_class = ReservaService

    def post(self, request):
        try:
            datos = json.loads(request.body or "{}")
            reserva = self.service_class().crear_reserva(cliente=request.user, datos=datos)
            return JsonResponse(
                {"id": reserva.pk, "estado": reserva.estado, "total": str(reserva.total)},
                status=201,
            )
        except (json.JSONDecodeError, ReservaError) as error:
            return JsonResponse({"error": str(error)}, status=400)
