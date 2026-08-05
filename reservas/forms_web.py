"""Formulario HTML para crear una reserva desde el navegador.

Es una interfaz alterna al endpoint JSON (`forms.CrearReservaForm`): ambos
arman el mismo `CrearReservaCommand` y llaman al mismo `ReservaService`.

El formulario se construye SIEMPRE alrededor de un servicio ya elegido. Con
eso, los horarios y las zonas que se ofrecen son solo los de ese profesional,
y las reglas RN-02 y RN-07 se vuelven imposibles de violar desde la interfaz.
El Builder las sigue validando igual: la interfaz evita el error, el dominio
lo garantiza.
"""

from django import forms

from .dto import CrearReservaCommand, LineaSolicitada
from .models import BloqueDisponibilidad, Reserva


class CrearReservaWebForm(forms.Form):
    bloque = forms.ModelChoiceField(
        queryset=BloqueDisponibilidad.objects.none(),
        label="Horario disponible",
        empty_label=None,
    )
    zona = forms.ChoiceField(choices=(), label="Zona")
    direccion = forms.CharField(max_length=180, label="Direccion")
    cantidad = forms.IntegerField(min_value=1, max_value=10, initial=1)

    def __init__(self, *args, servicio, **kwargs):
        super().__init__(*args, **kwargs)
        self.servicio = servicio
        profesional = servicio.profesional

        self.fields["bloque"].queryset = (
            BloqueDisponibilidad.objects.filter(
                profesional=profesional,
                estado=BloqueDisponibilidad.Estado.LIBRE,
            )
            .exclude(reservas__estado__in=Reserva.ESTADOS_ACTIVOS)
            .order_by("inicio")
        )
        self.fields["zona"].choices = [(z, z) for z in profesional.zonas_lista()]

    def a_comando(self, usuario_id: int) -> CrearReservaCommand:
        datos = self.cleaned_data
        return CrearReservaCommand(
            usuario_id=usuario_id,
            bloque_id=datos["bloque"].pk,
            direccion=datos["direccion"],
            zona=datos["zona"],
            lineas=(
                LineaSolicitada(
                    servicio_id=self.servicio.pk, cantidad=datos["cantidad"]
                ),
            ),
        )
