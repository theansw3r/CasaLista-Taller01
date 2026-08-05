"""
Modelos del modulo *Agenda y Reservas* (y las entidades de *Cuentas y Catalogo*
que necesita para funcionar).

Los modelos guardan estado y el comportamiento que es intrinsecamente suyo
(por ejemplo: si un bloque esta libre, cuanto suma una linea). Las reglas que
coordinan varias entidades NO viven aqui: viven en el Builder y en el Service.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from .domain.dinero import a_dinero


class Cliente(models.Model):
    """Quien solicita y paga la visita."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cliente"
    )
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "Clientes"

    def __str__(self) -> str:
        return self.nombre


class Profesional(models.Model):
    """Quien ofrece servicios y ejecuta la visita."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profesional"
    )
    nombre = models.CharField(max_length=120)
    verificado = models.BooleanField(
        default=False, help_text="RN-07: solo los verificados pueden recibir reservas."
    )
    zonas_cobertura = models.CharField(
        max_length=255,
        blank=True,
        help_text="Zonas atendidas, separadas por coma. Ej: Laureles,Belen,Envigado",
    )
    calificacion_promedio = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        verbose_name_plural = "Profesionales"

    def __str__(self) -> str:
        return self.nombre

    def zonas_lista(self) -> list[str]:
        """Zonas cubiertas, ya limpias. Alimenta el desplegable del formulario."""
        return [z.strip() for z in self.zonas_cobertura.split(",") if z.strip()]

    def cubre_zona(self, zona: str) -> bool:
        """RN-07: la cobertura del profesional debe incluir la zona del cliente."""
        objetivo = (zona or "").strip().casefold()
        if not objetivo:
            return False
        return objetivo in {z.casefold() for z in self.zonas_lista()}


class Servicio(models.Model):
    """Item del catalogo, con precio base y duracion estimada."""

    profesional = models.ForeignKey(
        Profesional, on_delete=models.CASCADE, related_name="servicios"
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_minutos = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Servicios"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.profesional.nombre})"

    def calcular_precio(self, cantidad: int = 1) -> Decimal:
        return a_dinero(self.precio_base * cantidad)


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

    def __str__(self) -> str:
        # Django devuelve datetimes en UTC al leerlos de la base; hay que
        # convertirlos a la zona local antes de mostrarlos.
        inicio = timezone.localtime(self.inicio)
        fin = timezone.localtime(self.fin)
        return f"{self.profesional.nombre}: {inicio:%d/%m %H:%M}-{fin:%H:%M}"

    @property
    def duracion_minutos(self) -> int:
        return int((self.fin - self.inicio).total_seconds() // 60)

    def esta_libre(self) -> bool:
        return self.estado == self.Estado.LIBRE

    def ocupar(self) -> None:
        self.estado = self.Estado.OCUPADO

    def liberar(self) -> None:
        self.estado = self.Estado.LIBRE

    def se_solapa_con(self, otro: "BloqueDisponibilidad") -> bool:
        return self.inicio < otro.fin and otro.inicio < self.fin


class Reserva(models.Model):
    """Acuerdo entre cliente y profesional. Es la raiz del flujo de negocio."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de pago"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    ESTADOS_ACTIVOS = (Estado.PENDIENTE, Estado.CONFIRMADA)

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
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tarifa_aplicada = models.CharField(
        max_length=20,
        default="BASE",
        help_text="Estrategia de tarifa usada al momento de reservar (trazabilidad).",
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Reservas"
        ordering = ["-creada_en"]

    def __str__(self) -> str:
        return f"Reserva #{self.pk} - {self.estado}"

    def esta_activa(self) -> bool:
        return self.estado in self.ESTADOS_ACTIVOS

    def calcular_total(self) -> Decimal:
        """Suma de los subtotales ya congelados en las lineas."""
        return a_dinero(sum((d.calcular_subtotal() for d in self.detalles.all()), Decimal("0")))

    def duracion_total_minutos(self) -> int:
        return sum(d.duracion_total() for d in self.detalles.all())


class DetalleReserva(models.Model):
    """Linea de la reserva: un servicio, su cantidad y el precio congelado.

    El precio se copia al reservar: si el profesional lo cambia despues, la
    reserva ya hecha conserva el valor acordado (nota de la seccion 2.2).
    """

    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name="detalles"
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="+")
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_unitaria_minutos = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Detalle de reserva"
        verbose_name_plural = "Detalles de reserva"

    def __str__(self) -> str:
        return f"{self.cantidad} x {self.servicio.nombre}"

    def calcular_subtotal(self) -> Decimal:
        return a_dinero(self.precio_unitario * self.cantidad)

    def duracion_total(self) -> int:
        return self.duracion_unitaria_minutos * self.cantidad
