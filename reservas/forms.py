"""
Validacion de FORMA (no de negocio) de la peticion HTTP.

Aqui solo se responde "¿los datos que llegaron tienen la forma esperada?".
Si el profesional cubre la zona o si el bloque esta libre son preguntas de
negocio y se responden en el dominio.
"""

import json

from django import forms

from .dto import CrearReservaCommand, LineaSolicitada


def datos_del_request(request):
    """Extrae el cuerpo del request acepte o no JSON, sin ensuciar la vista."""
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or "{}")
        except ValueError:
            return {}
    return request.POST


class CrearReservaForm(forms.Form):
    bloque_id = forms.IntegerField(min_value=1)
    direccion = forms.CharField(max_length=180)
    zona = forms.CharField(max_length=80)
    servicios = forms.JSONField(
        help_text='Ej: [{"servicio_id": 1, "cantidad": 2}]',
    )

    def clean_servicios(self) -> tuple[LineaSolicitada, ...]:
        crudo = self.cleaned_data["servicios"]
        if not isinstance(crudo, list) or not crudo:
            raise forms.ValidationError("Envie una lista con al menos un servicio.")
        try:
            lineas = tuple(
                LineaSolicitada(
                    servicio_id=int(item["servicio_id"]),
                    cantidad=int(item.get("cantidad", 1)),
                )
                for item in crudo
            )
        except (TypeError, KeyError, ValueError):
            raise forms.ValidationError(
                'Cada elemento debe ser {"servicio_id": <int>, "cantidad": <int>}.'
            ) from None
        return lineas

    def a_comando(self, usuario_id: int) -> CrearReservaCommand:
        """Traduce el formulario validado al comando que espera el Service."""
        datos = self.cleaned_data
        return CrearReservaCommand(
            usuario_id=usuario_id,
            bloque_id=datos["bloque_id"],
            direccion=datos["direccion"],
            zona=datos["zona"],
            lineas=datos["servicios"],
        )
