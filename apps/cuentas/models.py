from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Cliente(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cliente",
        help_text="Cuenta de acceso. Un usuario tiene como maximo un perfil de cliente.",
    )
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Profesional(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profesional",
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(
        blank=True,
        help_text="Como se presenta: oficio, experiencia, que trabajos hace.",
    )
    documento = models.CharField(
        max_length=30,
        unique=True,
        help_text="Documento de identidad. Lo usa el administrador para verificar.",
    )
    verificado = models.BooleanField(
        default=False,
        help_text="RN-07: solo un profesional verificado puede recibir reservas.",
    )
    zonas_cobertura = models.CharField(
        max_length=255,
        blank=True,
        help_text="Zonas atendidas separadas por coma. Ej: Laureles,Belen,Envigado",
    )
    calificacion_promedio = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("5"))],
        help_text="Lo recalcula el modulo de Reputacion (Entrega 2).",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profesional"
        verbose_name_plural = "Profesionales"
        ordering = ["-calificacion_promedio", "nombre"]
        indexes = [
            models.Index(fields=["verificado"], name="idx_profesional_verificado"),
        ]

    def __str__(self) -> str:
        return self.nombre
