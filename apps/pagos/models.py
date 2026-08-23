"""
Modelos del modulo *Pagos y Liquidacion*.

Esta entrega implementa Pago. Liquidacion queda para la Entrega 2 (ver el
alcance en docs/wiki/01-Modelo-de-Dominio.md).

Segun el diagrama, la relacion Reserva - Pago es 1 a 0..1: una reserva genera
como maximo un pago. Eso se expresa con un OneToOneField, no con un
ForeignKey: la cardinalidad la garantiza la base de datos y no un `if` que
alguien pueda olvidar.

Como en el resto del proyecto, el modelo solo declara datos. `procesar()`,
`reembolsar()` y `estaAprobado()` del diagrama viven en `dominio/`.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.reservas.models import Reserva


class Pago(models.Model):
    """Movimiento de dinero del cliente hacia la plataforma."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        REEMBOLSADO = "REEMBOLSADO", "Reembolsado"

    class Medio(models.TextChoices):
        TARJETA = "TARJETA", "Tarjeta de credito o debito"
        PSE = "PSE", "PSE (debito bancario)"

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.PROTECT,
        related_name="pago",
        help_text="1 reserva genera 0..1 pago.",
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Se copia del total de la reserva al momento de cobrar.",
    )
    medio = models.CharField(max_length=10, choices=Medio.choices)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    pasarela = models.CharField(
        max_length=20,
        help_text="Que pasarela lo proceso. Sin esto no se puede conciliar.",
    )
    referencia_externa = models.CharField(
        max_length=64,
        blank=True,
        help_text="Identificador que devuelve la pasarela. Es la prueba del cobro.",
    )
    motivo_rechazo = models.CharField(max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado"], name="idx_pago_estado"),
        ]

    def __str__(self) -> str:
        return f"Pago #{self.pk} de reserva #{self.reserva_id} ({self.estado})"
