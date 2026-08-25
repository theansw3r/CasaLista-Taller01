from django.contrib import admin

from apps.cuentas.models import Cliente, Profesional
from apps.cuentas.services import VerificacionProfesionalService


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "telefono", "creado_en"]
    search_fields = ["nombre", "usuario__email"]


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ["nombre", "verificado", "zonas_cobertura", "calificacion_promedio"]
    list_filter = ["verificado"]
    search_fields = ["nombre", "documento"]
    actions = ["verificar", "revocar"]

    # El admin no decide nada: delega en el servicio, igual que una vista.
    servicio = VerificacionProfesionalService

    @admin.action(description="Verificar los profesionales seleccionados")
    def verificar(self, request, queryset):
        cuantos = self.servicio().verificar(queryset)
        self.message_user(request, f"{cuantos} profesional(es) verificado(s).")

    @admin.action(description="Quitar la verificacion")
    def revocar(self, request, queryset):
        cuantos = self.servicio().revocar(queryset)
        self.message_user(request, f"{cuantos} profesional(es) sin verificar.")
