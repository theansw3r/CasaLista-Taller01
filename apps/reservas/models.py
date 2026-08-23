"""
Modelos del modulo *Agenda y Reservas*.

Corresponden a BloqueDisponibilidad, Reserva y DetalleReserva del diagrama.
El Business Case los agrupa en un solo modulo porque cambian juntos: no existe
una reserva sin una franja que ocupar.

Los tres modelos son deliberadamente "delgados": campos, restricciones de
integridad, `Meta` y `__str__`. Los metodos que el diagrama les asigna
(`calcularTotal`, `estaLibre`, `confirmar`, `cancelar`, `calcularSubtotal`)
estan implementados en `dominio/`, cada uno en la clase que corresponde:

    estaLibre / ocupar / seSolapaCon -> dominio/agenda.py
    calcularTotal / calcularSubtotal -> dominio/precios.py
    confirmar / cancelar             -> dominio/ciclo_de_vida.py
    calcularPenalizacion             -> dominio/cancelacion.py

Lo que si vive aqui son las restricciones que debe garantizar la base de
datos, porque una regla que solo se comprueba en Python se rompe en cuanto
hay dos procesos escribiendo a la vez.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.catalogo.models import Servicio
from apps.cuentas.models import Cliente, Profesional


class BloqueDisponibilidad(models.Model):
    """Franja horaria concreta que un profesional publica en su agenda."""

    class Estado(models.TextChoices):
        LIBRE = "LIBRE", "Libre"
        OCUPADO = "OCUPADO", "Ocupado"

    profesional = models.ForeignKey(
        Profesional, on_delete=models.CASCADE, related_name="bloques"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.LIBRE
    )

    class Meta:
        verbose_name = "Bloque de disponibilidad"
        verbose_name_plural = "Bloques de disponibilidad"
        ordering = ["inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gt=models.F("inicio")),
                name="bloque_termina_despues_de_empezar",
            ),
            # Un profesional no puede publicar dos veces exactamente la misma
            # franja. El solapamiento parcial no se puede expresar con una
            # restriccion portable, asi que lo valida AgendaService.
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
        # Django guarda en UTC; se convierte a la zona del negocio solo para
        # mostrar. Es formato, no una regla.
        inicio = timezone.localtime(self.inicio)
        fin = timezone.localtime(self.fin)
        return f"{self.profesional.nombre}: {inicio:%d/%m %H:%M}-{fin:%H:%M}"


class Reserva(models.Model):
    """Acuerdo entre cliente y profesional. Es la raiz del agregado."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de pago"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

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
        help_text="Lo calcula la estrategia de tarifa al construir la reserva.",
    )
    tarifa_aplicada = models.CharField(
        max_length=20,
        default="BASE",
        help_text="Que estrategia se uso. Sin esto un total no se puede auditar.",
    )
    penalizacion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="RN-04: monto retenido si el cliente cancela.",
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-creada_en"]
        indexes = [
            models.Index(fields=["cliente", "-creada_en"], name="idx_reserva_cliente"),
            models.Index(fields=["estado"], name="idx_reserva_estado"),
        ]

    def __str__(self) -> str:
        return f"Reserva #{self.pk} ({self.estado})"


class DetalleReserva(models.Model):
    """Linea de la reserva: un servicio, su cantidad y el precio congelado.

    Congelar el precio no es una optimizacion: es la nota del modelo de
    dominio (seccion 2.2). Si el profesional sube el precio del servicio
    manana, la reserva de hoy conserva lo que se acordo hoy.
    """

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,  # Composicion: sin reserva no hay detalle.
        related_name="detalles",
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="+")
    cantidad = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_unitaria_minutos = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Detalle de reserva"
        verbose_name_plural = "Detalles de reserva"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="detalle_cantidad_positiva",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cantidad} x {self.servicio.nombre}"
