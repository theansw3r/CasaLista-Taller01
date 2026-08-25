from django.contrib import admin

from apps.catalogo.models import Servicio


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ["nombre", "profesional", "precio_base", "duracion_minutos", "activo"]
    list_filter = ["activo", "requiere_visita_previa"]
    search_fields = ["nombre", "profesional__nombre"]
