from django.urls import path

from apps.pagos.api.views import PagoDetalleView, ProcesarPagoView

app_name = "pagos"

urlpatterns = [
    path("", ProcesarPagoView.as_view(), name="procesar"),
    path("<int:pago_id>/", PagoDetalleView.as_view(), name="detalle"),
]
