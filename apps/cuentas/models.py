"""
Modelos del modulo *Cuentas*.

Corresponden a las clases Usuario, Cliente y Profesional del diagrama de
dominio.

Decision importante de esta entrega
-----------------------------------
Los modelos guardan ESTADO y nada mas. No tienen metodos que calculen,
validen o decidan: eso vive en `dominio/` (reglas) y en `services.py`
(orquestacion). Un modelo aqui responde "que datos soy", nunca "que puedo
hacer".

La clase abstracta `Usuario` del diagrama se resuelve con el `User` de
django.contrib.auth (autenticacion, hash de contrasena, permisos) mas un
perfil por rol. Es la traduccion estandar de una herencia de dominio a Django:
heredar de AbstractUser habria obligado a un unico tipo de cuenta, y un mismo
correo puede ser cliente hoy y profesional manana.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Cliente(models.Model):
    """Quien solicita y paga la visita."""

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
    """Quien ofrece servicios y ejecuta la visita."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profesional",
    )
    nombre = models.CharField(max_length=120)
    documento = models.CharField(
        max_length=30,
        unique=True,
        help_text="Documento de identidad. Lo usa el administrador para verificar.",
    )
    verificado = models.BooleanField(
        default=False,
        help_text="RN-07: solo un profesional verificado puede recibir reservas.",
    )
    # Se guarda como texto separado por comas por simplicidad de esta entrega.
    # La normalizacion en una tabla ZonaCobertura esta anotada como deuda
    # tecnica en la wiki (03-Patrones-Creacionales, seccion de limitaciones).
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
            # La busqueda del catalogo filtra siempre por verificado.
            models.Index(fields=["verificado"], name="idx_profesional_verificado"),
        ]

    def __str__(self) -> str:
        return self.nombre
