from django.contrib import admin

from .models import (
    BloqueDisponibilidad,
    Cliente,
    DetalleReserva,
    Profesional,
    Reserva,
    Servicio,
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "usuario")


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "verificado", "zonas_cobertura", "calificacion_promedio")
    list_filter = ("verificado",)


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "profesional", "precio_base", "duracion_minutos", "activo")
    list_filter = ("activo", "profesional")


@admin.register(BloqueDisponibilidad)
class BloqueDisponibilidadAdmin(admin.ModelAdmin):
    list_display = ("profesional", "inicio", "fin", "estado")
    list_filter = ("estado", "profesional")


class DetalleReservaInline(admin.TabularInline):
    model = DetalleReserva
    extra = 0


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "profesional", "estado", "total", "creada_en")
    list_filter = ("estado", "tarifa_aplicada")
    inlines = [DetalleReservaInline]
