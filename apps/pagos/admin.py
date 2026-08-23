"""Admin del modulo Pagos."""

from django.contrib import admin

from apps.pagos.models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["id", "reserva", "monto", "medio", "estado", "pasarela", "creado_en"]
    list_filter = ["estado", "medio", "pasarela"]
    # Un pago es un hecho contable: se consulta, no se edita.
    readonly_fields = [f.name for f in Pago._meta.fields]
