"""
Carga un catalogo realista: los cinco oficios del Business Case, con sus
servicios, sus zonas de cobertura y agenda libre para los proximos dias.

    python manage.py sembrar_catalogo
    python manage.py sembrar_catalogo --limpiar   # borra antes los datos de prueba

Es idempotente: correrlo dos veces no duplica profesionales ni servicios.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ...models import BloqueDisponibilidad, Cliente, Profesional, Reserva, Servicio

CATALOGO = [
    {
        "nombre": "Pedro Osorio",
        "oficio": "Plomeria",
        "zonas": "Laureles,Belen,Estadio,La America",
        "servicios": [
            ("Reparacion de fuga", "80000", 60),
            ("Cambio de sifon", "45000", 30),
            ("Instalacion de lavamanos", "120000", 90),
        ],
    },
    {
        "nombre": "Luis Cardona",
        "oficio": "Electricidad",
        "zonas": "El Poblado,Envigado,Sabaneta",
        "servicios": [
            ("Cambio de toma corriente", "40000", 30),
            ("Revision de tablero electrico", "95000", 60),
            ("Instalacion de lampara", "55000", 45),
        ],
    },
    {
        "nombre": "Marta Quintero",
        "oficio": "Reparacion de electrodomesticos",
        "zonas": "Laureles,El Poblado,Envigado,Itagui",
        "servicios": [
            ("Reparacion de nevera", "150000", 120),
            ("Reparacion de lavadora", "130000", 90),
        ],
    },
    {
        "nombre": "Andres Gomez",
        "oficio": "Pintura",
        "zonas": "Belen,Itagui,Sabaneta,Robledo",
        "servicios": [
            ("Pintura de habitacion", "180000", 240),
            ("Retoque de humedad", "90000", 120),
        ],
    },
    {
        "nombre": "Carolina Ruiz",
        "oficio": "Cerrajeria",
        "zonas": "Laureles,Estadio,Robledo,Bello",
        "servicios": [
            ("Apertura de puerta", "70000", 30),
            ("Cambio de guarda", "110000", 60),
        ],
    },
]

# Franjas del dia. Las 19:00 sirven para ver el recargo de TARIFA_TYPE=DINAMICA.
HORAS = (8, 14, 19)
DIAS_DE_AGENDA = 7


class Command(BaseCommand):
    help = "Siembra los cinco oficios del Business Case con agenda disponible."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra reservas y los profesionales de prueba antes de sembrar.",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        if opciones["limpiar"]:
            self._limpiar()

        for ficha in CATALOGO:
            profesional = self._crear_profesional(ficha)
            servicios = [self._crear_servicio(profesional, s) for s in ficha["servicios"]]
            bloques = self._crear_agenda(profesional)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{profesional.nombre:20} {ficha['oficio']:32} "
                    f"{len(servicios)} servicios, {bloques} bloques libres"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            f"Listo: {Profesional.objects.filter(verificado=True).count()} profesionales "
            f"verificados, {Servicio.objects.filter(activo=True).count()} servicios, "
            f"{BloqueDisponibilidad.objects.filter(estado=BloqueDisponibilidad.Estado.LIBRE).count()} "
            f"bloques libres."
        )
        self.stdout.write("Entra a http://127.0.0.1:8000/reservar/ para reservar.")

    # ------------------------------------------------------------------
    def _limpiar(self):
        """Borra SOLO los datos que generan los comandos de demostracion."""
        usuarios_de_prueba = User.objects.filter(
            username__in=[
                "verificacion@casalista.co",
                "profesional-verificacion@casalista.co",
                "pedro@casalista.co",
            ]
        )
        Reserva.objects.all().delete()
        BloqueDisponibilidad.objects.all().delete()
        Cliente.objects.filter(usuario__in=usuarios_de_prueba).delete()
        Profesional.objects.filter(usuario__in=usuarios_de_prueba).delete()
        usuarios_de_prueba.delete()
        self.stdout.write(self.style.WARNING("Datos de prueba borrados."))
        self.stdout.write("")

    def _crear_profesional(self, ficha) -> Profesional:
        correo = ficha["nombre"].lower().replace(" ", ".") + "@casalista.co"
        usuario, _ = User.objects.get_or_create(
            username=correo, defaults={"email": correo}
        )
        profesional, creado = Profesional.objects.get_or_create(
            usuario=usuario,
            defaults={
                "nombre": ficha["nombre"],
                "verificado": True,
                "zonas_cobertura": ficha["zonas"],
            },
        )
        if not creado:
            profesional.zonas_cobertura = ficha["zonas"]
            profesional.verificado = True
            profesional.save(update_fields=["zonas_cobertura", "verificado"])
        return profesional

    def _crear_servicio(self, profesional, ficha_servicio) -> Servicio:
        nombre, precio, duracion = ficha_servicio
        servicio, _ = Servicio.objects.get_or_create(
            profesional=profesional,
            nombre=nombre,
            defaults={
                "precio_base": Decimal(precio),
                "duracion_minutos": duracion,
                "activo": True,
            },
        )
        return servicio

    def _crear_agenda(self, profesional) -> int:
        """Crea bloques de 4 horas para los proximos dias, sin duplicar."""
        hoy = timezone.localtime(timezone.now()).replace(
            minute=0, second=0, microsecond=0
        )
        creados = 0
        for dia in range(1, DIAS_DE_AGENDA + 1):
            for hora in HORAS:
                inicio = (hoy + timedelta(days=dia)).replace(hour=hora)
                if BloqueDisponibilidad.objects.filter(
                    profesional=profesional, inicio=inicio
                ).exists():
                    continue
                BloqueDisponibilidad.objects.create(
                    profesional=profesional,
                    inicio=inicio,
                    fin=inicio + timedelta(hours=4),
                )
                creados += 1
        return creados
