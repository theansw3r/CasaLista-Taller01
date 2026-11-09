from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.cuentas.models import Profesional


class Servicio(models.Model):

    class Oficio(models.TextChoices):
        """Los cinco oficios del nicho (Business Case, seccion 1.1).

        No es una lista abierta a proposito: acotar el catalogo a servicios con
        duracion estimable es lo que permite modelar una agenda real y no un
        formulario de contacto.
        """

        PLOMERIA = "PLOMERIA", _lazy("Plomeria")
        ELECTRICIDAD = "ELECTRICIDAD", _lazy("Electricidad")
        ELECTRODOMESTICOS = "ELECTRODOMESTICOS", _lazy("Reparacion de electrodomesticos")
        PINTURA = "PINTURA", _lazy("Pintura")
        CERRAJERIA = "CERRAJERIA", _lazy("Cerrajeria")

    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.CASCADE,
        related_name="servicios",
        help_text=_lazy("Agregacion: 1 profesional ofrece 1..* servicios."),
    )
    categoria = models.CharField(
        max_length=20,
        choices=Oficio.choices,
        help_text=_lazy("Oficio al que pertenece. Solo los cinco del nicho."),
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(
        help_text=_lazy("Que incluye la visita. El cliente decide con esto."),
    )
    precio_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_lazy("Precio publicado. Se congela en la linea al reservar."),
    )
    duracion_minutos = models.PositiveIntegerField(
        validators=[MinValueValidator(60), MaxValueValidator(240)],
        help_text=_lazy("Duracion de la visita: entre 1 y 4 horas (Business Case 1.1)."),
    )
    requiere_visita_previa = models.BooleanField(
        default=False,
        help_text=_lazy("Trabajos que necesitan diagnostico antes de cotizar en firme."),
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _lazy("Servicio")
        verbose_name_plural = _lazy("Servicios")
        ordering = ["categoria", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["profesional", "nombre"],
                name="unico_nombre_de_servicio_por_profesional",
            )
        ]

        indexes = [
            models.Index(fields=["categoria", "activo"], name="idx_servicio_oficio"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.profesional.nombre})"
