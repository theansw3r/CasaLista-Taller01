"""
Carga un escenario minimo y ejecuta el caso de uso desde la consola.

Sirve para demostrar el Patron Factory sin levantar el servidor:

    set NOTIFICADOR_TYPE=MOCK  &&  python manage.py sembrar_demo
    set NOTIFICADOR_TYPE=REAL  &&  python manage.py sembrar_demo

El mismo Service, el mismo Builder y el mismo comando producen dos
comportamientos distintos porque la Factory resuelve otra implementacion.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...dto import CrearReservaCommand, LineaSolicitada
from ...infra.factories import CalculadorTarifaFactory, NotificadorFactory
from ...models import BloqueDisponibilidad, Cliente, Profesional, Reserva, Servicio
from ...services import ReservaService


class Command(BaseCommand):
    help = "Siembra datos de demostracion y crea una reserva de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-datos",
            action="store_true",
            help="Siembra los datos pero no crea la reserva de ejemplo.",
        )

    def handle(self, *args, **opciones):
        cliente, profesional, servicios, bloque = self._sembrar()

        self.stdout.write(self.style.SUCCESS("Datos de demostracion listos:"))
        self.stdout.write(f"  Cliente      : {cliente.nombre} (usuario={cliente.usuario.username})")
        self.stdout.write(f"  Profesional  : {profesional.nombre} (verificado, zonas={profesional.zonas_cobertura})")
        for servicio in servicios:
            self.stdout.write(
                f"  Servicio #{servicio.pk:<3}: {servicio.nombre} - $ {servicio.precio_base} - {servicio.duracion_minutos} min"
            )
        inicio_local = timezone.localtime(bloque.inicio)
        fin_local = timezone.localtime(bloque.fin)
        self.stdout.write(
            f"  Bloque #{bloque.pk:<4}: {inicio_local:%d/%m/%Y %H:%M} a {fin_local:%H:%M}"
        )

        self.stdout.write("")
        self.stdout.write("Implementaciones resueltas por las Factories:")
        self.stdout.write(f"  NOTIFICADOR_TYPE -> {type(NotificadorFactory.crear()).__name__}")
        self.stdout.write(f"  TARIFA_TYPE      -> {type(CalculadorTarifaFactory.crear()).__name__}")

        if opciones["solo_datos"]:
            return

        self.stdout.write("")
        self.stdout.write("Ejecutando ReservaService.crear_reserva()...")
        reserva = ReservaService().crear_reserva(
            CrearReservaCommand(
                usuario_id=cliente.usuario_id,
                bloque_id=bloque.pk,
                direccion="Calle 30 #45-12",
                zona="Laureles",
                lineas=(LineaSolicitada(servicio_id=servicios[0].pk, cantidad=1),),
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Reserva #{reserva.pk} creada | estado={reserva.estado} | "
                f"total=$ {reserva.total} | tarifa={reserva.tarifa_aplicada}"
            )
        )

    # ------------------------------------------------------------------
    def _sembrar(self):
        usuario_cliente, _ = User.objects.get_or_create(
            username="ana@casalista.co", defaults={"email": "ana@casalista.co"}
        )
        cliente, _ = Cliente.objects.get_or_create(
            usuario=usuario_cliente,
            defaults={"nombre": "Ana Restrepo", "telefono": "3001234567"},
        )

        usuario_pro, _ = User.objects.get_or_create(
            username="pedro@casalista.co", defaults={"email": "pedro@casalista.co"}
        )
        profesional, _ = Profesional.objects.get_or_create(
            usuario=usuario_pro,
            defaults={
                "nombre": "Pedro Osorio",
                "verificado": True,
                "zonas_cobertura": "Laureles,Belen,Envigado",
            },
        )

        catalogo = [
            ("Reparacion de fuga", Decimal("80000"), 60),
            ("Cambio de sifon", Decimal("45000"), 30),
        ]
        servicios = []
        for nombre, precio, duracion in catalogo:
            servicio, _ = Servicio.objects.get_or_create(
                profesional=profesional,
                nombre=nombre,
                defaults={"precio_base": precio, "duracion_minutos": duracion},
            )
            servicios.append(servicio)

        # Franja nocturna a proposito: asi TARIFA_TYPE=DINAMICA muestra el
        # recargo del 20 % frente a TARIFA_TYPE=BASE.
        inicio = (timezone.localtime(timezone.now()) + timedelta(days=1)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
        bloque = (
            BloqueDisponibilidad.objects.filter(
                profesional=profesional, estado=BloqueDisponibilidad.Estado.LIBRE
            )
            .exclude(reservas__estado__in=Reserva.ESTADOS_ACTIVOS)
            .first()
        )
        if bloque is None:
            bloque = BloqueDisponibilidad.objects.create(
                profesional=profesional, inicio=inicio, fin=inicio + timedelta(hours=2)
            )

        return cliente, profesional, servicios, bloque
