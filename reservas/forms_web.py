"""Formulario HTML para crear una reserva desde el navegador.

Es una alternativa de interfaz al endpoint JSON (`forms.CrearReservaForm`):
ambos terminan armando el mismo `CrearReservaCommand` y llamando al mismo
`ReservaService`. Eso es lo que demuestra que la logica no depende de HTTP.
"""

from django import forms

from .dto import CrearReservaCommand, LineaSolicitada
from .models import BloqueDisponibilidad, Servicio


class CrearReservaWebForm(forms.Form):
    servicio = forms.ModelChoiceField(
        queryset=Servicio.objects.filter(
            activo=True, profesional__verificado=True
        ).select_related("profesional"),
        label="Servicio",
    )
    bloque = forms.ModelChoiceField(
        queryset=BloqueDisponibilidad.objects.filter(
            estado=BloqueDisponibilidad.Estado.LIBRE
        ).select_related("profesional"),
        label="Horario disponible",
        help_text="Debe ser un bloque del mismo profesional que el servicio elegido.",
    )
    direccion = forms.CharField(max_length=180)
    zona = forms.CharField(max_length=80)

    def a_comando(self, usuario_id: int) -> CrearReservaCommand:
        servicio = self.cleaned_data["servicio"]
        bloque = self.cleaned_data["bloque"]
        return CrearReservaCommand(
            usuario_id=usuario_id,
            bloque_id=bloque.pk,
            direccion=self.cleaned_data["direccion"],
            zona=self.cleaned_data["zona"],
            lineas=(LineaSolicitada(servicio_id=servicio.pk, cantidad=1),),
        )
