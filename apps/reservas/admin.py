from django.contrib import admin

from apps.reservas.models import BloqueDisponibilidad, DetalleReserva, Reserva


class DetalleReservaInline(admin.TabularInline):
    model = DetalleReserva
    extra = 0
    readonly_fields = ["servicio", "cantidad", "precio_unitario", "duracion_unitaria_minutos"]
    can_delete = False


@admin.register(BloqueDisponibilidad)
class BloqueDisponibilidadAdmin(admin.ModelAdmin):
    list_display = ["profesional", "inicio", "fin", "estado"]
    list_filter = ["estado", "profesional"]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["id", "cliente", "profesional", "estado", "total", "tarifa_aplicada", "creada_en"]
    list_filter = ["estado", "tarifa_aplicada"]
    search_fields = ["cliente__nombre", "profesional__nombre"]
    readonly_fields = ["total", "tarifa_aplicada", "penalizacion", "creada_en"]
    inlines = [DetalleReservaInline]
