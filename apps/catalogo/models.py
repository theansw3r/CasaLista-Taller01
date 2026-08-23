"""
Modelos del modulo *Catalogo*.

Corresponde a la clase Servicio del diagrama de dominio.

El Business Case (seccion 3) agrupa Cuentas y Catalogo en un solo modulo. Aqui
se separan en dos apps de Django por una razon concreta: cambian por motivos
distintos y se leen con frecuencias muy distintas. El catalogo es el endpoint
mas consultado del sistema (todo el mundo busca antes de reservar) y es el
primero que habria que poner detras de una cache o replicar. Tenerlo aislado
es lo que hace que esa decision sea posible sin tocar identidad.

Como en el resto del proyecto, el modelo solo declara datos: `calcularPrecio()`
del diagrama vive en `dominio/precios.py`.
"""

from django.core.validators import MinValueValidator
from django.db import models

from apps.cuentas.models import Profesional


class Servicio(models.Model):
    """Item del catalogo, con precio base y duracion estimada."""

    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.CASCADE,
        related_name="servicios",
        help_text="Agregacion: 1 profesional ofrece 1..* servicios.",
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Precio publicado. Se congela en la linea al reservar.",
    )
    duracion_minutos = models.PositiveIntegerField(
        validators=[MinValueValidator(15)],
        help_text="Duracion estimada de la visita. Nunca menos de 15 minutos.",
    )
    requiere_visita_previa = models.BooleanField(
        default=False,
        help_text="Trabajos que necesitan diagnostico antes de cotizar en firme.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["nombre"]
        constraints = [
            # Un profesional no publica dos veces el mismo servicio: la
            # unicidad la garantiza la base de datos, no un if en Python.
            models.UniqueConstraint(
                fields=["profesional", "nombre"],
                name="unico_nombre_de_servicio_por_profesional",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.profesional.nombre})"
