from django.utils.translation import gettext as _, gettext_lazy as _lazy
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.catalogo.models import Servicio
from apps.cuentas.models import Cliente, Profesional


class BloqueDisponibilidad(models.Model):

    class Estado(models.TextChoices):
        LIBRE = "LIBRE", _lazy("Libre")
        OCUPADO = "OCUPADO", _lazy("Ocupado")

    profesional = models.ForeignKey(
        Profesional, on_delete=models.CASCADE, related_name="bloques"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.LIBRE
    )

    class Meta:
        verbose_name = _lazy("Bloque de disponibilidad")
        verbose_name_plural = _lazy("Bloques de disponibilidad")
        ordering = ["inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gt=models.F("inicio")),
                name="bloque_termina_despues_de_empezar",
            ),
            models.UniqueConstraint(
                fields=["profesional", "inicio", "fin"],
                name="bloque_unico_por_profesional",
            ),
        ]
        indexes = [
            models.Index(
                fields=["profesional", "estado", "inicio"],
                name="idx_bloque_busqueda",
            ),
        ]

    def __str__(self) -> str:
        inicio = timezone.localtime(self.inicio)
        fin = timezone.localtime(self.fin)
        return f"{self.profesional.nombre}: {inicio:%d/%m %H:%M}-{fin:%H:%M}"


class Reserva(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", _lazy("Pendiente de pago")
        CONFIRMADA = "CONFIRMADA", _lazy("Confirmada")
        COMPLETADA = "COMPLETADA", _lazy("Completada")
        CANCELADA = "CANCELADA", _lazy("Cancelada")

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="reservas"
    )
    profesional = models.ForeignKey(
        Profesional, on_delete=models.PROTECT, related_name="reservas"
    )
    bloque = models.ForeignKey(
        BloqueDisponibilidad, on_delete=models.PROTECT, related_name="reservas"
    )
    direccion = models.CharField(max_length=180)
    zona = models.CharField(max_length=80)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_lazy("Lo calcula la estrategia de tarifa al construir la reserva."),
    )
    tarifa_aplicada = models.CharField(
        max_length=20,
        default="BASE",
        help_text=_lazy("Que estrategia se uso. Sin esto un total no se puede auditar."),
    )
    penalizacion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_lazy("RN-04: monto retenido si el cliente cancela."),
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _lazy("Reserva")
        verbose_name_plural = _lazy("Reservas")
        ordering = ["-creada_en"]
        indexes = [
            models.Index(fields=["cliente", "-creada_en"], name="idx_reserva_cliente"),
            models.Index(fields=["estado"], name="idx_reserva_estado"),
        ]

    def __str__(self) -> str:
        return f"Reserva #{self.pk} ({self.estado})"


class DetalleReserva(models.Model):

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="+")
    cantidad = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_unitaria_minutos = models.PositiveIntegerField()

    class Meta:
        verbose_name = _lazy("Detalle de reserva")
        verbose_name_plural = _lazy("Detalles de reserva")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="detalle_cantidad_positiva",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cantidad} x {self.servicio.nombre}"


class NotificacionPendiente(models.Model):
    """Outbox transaccional, único por confirmación de creación de reserva."""
    reserva = models.OneToOneField(Reserva, on_delete=models.PROTECT, related_name="notificacion")
    idioma = models.CharField(max_length=10, default="es")
    creada_en = models.DateTimeField(auto_now_add=True)
    enviada_en = models.DateTimeField(null=True, blank=True, db_index=True)
