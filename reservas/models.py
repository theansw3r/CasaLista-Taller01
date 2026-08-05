from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Profesional(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    verificado = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.nombre


class Servicio(models.Model):
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name="servicios",
    )
    nombre = models.CharField(max_length=120)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_minutos = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    def clean(self) -> None:
        if self.precio_base <= Decimal("0"):
            raise ValidationError({"precio_base": "El precio debe ser mayor que cero."})
        if self.duracion_minutos <= 0:
            raise ValidationError(
                {"duracion_minutos": "La duración debe ser mayor que cero."}
            )

    def __str__(self) -> str:
        return self.nombre


class BloqueDisponibilidad(models.Model):
    class Estado(models.TextChoices):
        LIBRE = "LIBRE", "Libre"
        OCUPADO = "OCUPADO", "Ocupado"

    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name="bloques",
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.LIBRE,
    )

    def clean(self) -> None:
        if self.fin <= self.inicio:
            raise ValidationError({"fin": "La fecha final debe ser posterior al inicio."})

    def esta_libre(self) -> bool:
        return self.estado == self.Estado.LIBRE

    def ocupar(self) -> None:
        if not self.esta_libre():
            raise ValidationError("El bloque ya se encuentra ocupado.")
        self.estado = self.Estado.OCUPADO

    def liberar(self) -> None:
        self.estado = self.Estado.LIBRE

    def __str__(self) -> str:
        return f"{self.profesional} — {self.inicio:%Y-%m-%d %H:%M}"


class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    bloque = models.ForeignKey(
        BloqueDisponibilidad,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(total__gte=Decimal("0")),
                name="reserva_total_no_negativo",
            ),
            models.UniqueConstraint(
                fields=["bloque"],
                condition=Q(
                    estado__in=[
                        "PENDIENTE",
                        "CONFIRMADA",
                        "EN_CURSO",
                    ]
                ),
                name="bloque_unico_en_reserva_activa",
            ),
        ]

    def clean(self) -> None:
        if self.total <= Decimal("0"):
            raise ValidationError({"total": "El total debe ser mayor que cero."})
        if self.bloque_id and self.profesional_id:
            if self.bloque.profesional_id != self.profesional_id:
                raise ValidationError(
                    "El bloque no pertenece al profesional de la reserva."
                )

    def __str__(self) -> str:
        return f"Reserva #{self.pk or 'nueva'} — {self.estado}"


class DetalleReserva(models.Model):
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        related_name="detalles_reserva",
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad

    def clean(self) -> None:
        if self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor que cero."})
        if self.precio_unitario <= Decimal("0"):
            raise ValidationError(
                {"precio_unitario": "El precio debe ser mayor que cero."}
            )

    def __str__(self) -> str:
        return f"{self.servicio} x {self.cantidad}"
