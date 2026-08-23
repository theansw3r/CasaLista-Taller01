"""Admin del modulo Cuentas: sirve para verificar profesionales (RN-07)."""

from django.contrib import admin

from apps.cuentas.models import Cliente, Profesional


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "telefono", "creado_en"]
    search_fields = ["nombre", "usuario__email"]


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ["nombre", "verificado", "zonas_cobertura", "calificacion_promedio"]
    list_filter = ["verificado"]
    search_fields = ["nombre", "documento"]
    # Verificar es la accion del administrador que habilita RN-07.
    actions = ["verificar"]

    @admin.action(description="Verificar los profesionales seleccionados")
    def verificar(self, request, queryset):
        actualizados = queryset.update(verificado=True)
        self.message_user(request, f"{actualizados} profesional(es) verificado(s).")
