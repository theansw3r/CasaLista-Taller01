from django.utils.translation import gettext as _, gettext_lazy as _lazy
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.reservas.models import Reserva


class Pago(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", _lazy("Pendiente")
        APROBADO = "APROBADO", _lazy("Aprobado")
        RECHAZADO = "RECHAZADO", _lazy("Rechazado")
        REEMBOLSADO = "REEMBOLSADO", _lazy("Reembolsado")

    class Medio(models.TextChoices):
        TARJETA = "TARJETA", _lazy("Tarjeta de credito o debito")
        PSE = "PSE", _lazy("PSE (debito bancario)")

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.PROTECT,
        related_name="pago",
        help_text=_lazy("1 reserva genera 0..1 pago."),
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_lazy("Se copia del total de la reserva al momento de cobrar."),
    )
    medio = models.CharField(max_length=10, choices=Medio.choices)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    pasarela = models.CharField(
        max_length=20,
        help_text=_lazy("Que pasarela lo proceso. Sin esto no se puede conciliar."),
    )
    referencia_externa = models.CharField(
        max_length=64,
        blank=True,
        help_text=_lazy("Identificador que devuelve la pasarela. Es la prueba del cobro."),
    )
    motivo_rechazo = models.CharField(max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _lazy("Pago")
        verbose_name_plural = _lazy("Pagos")
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado"], name="idx_pago_estado"),
        ]

    def __str__(self) -> str:
        return f"Pago #{self.pk} de reserva #{self.reserva_id} ({self.estado})"
