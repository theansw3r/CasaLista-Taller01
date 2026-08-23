"""
Datos de demostracion para la sustentacion.

Se apoya en los MISMOS servicios que usa la API. No crea reservas con
`Reserva.objects.create(...)`: llama a `ReservaService`, que llama al Builder,
que valida las reglas. Es la prueba practica de que la capa de aplicacion es
independiente de HTTP: el mismo caso de uso corre desde una peticion REST y
desde una linea de comandos, sin duplicar una sola regla.

    python manage.py sembrar_demo
    python manage.py sembrar_demo --reiniciar
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Servicio
from apps.cuentas.dto import RegistrarClienteCommand, RegistrarProfesionalCommand
from apps.cuentas.models import Cliente, Profesional
from apps.cuentas.services import RegistroClienteService, RegistroProfesionalService
from apps.pagos.dto import ProcesarPagoCommand
from apps.pagos.models import Pago
from apps.pagos.services import PagoService
from apps.reservas.dto import (
    AbrirDisponibilidadCommand,
    CrearReservaCommand,
    LineaSolicitada,
)
from apps.reservas.models import BloqueDisponibilidad, DetalleReserva, Reserva
from apps.reservas.services import AgendaService, ReservaService

Usuario = get_user_model()

CONTRASENA = "casalista2026"


class Command(BaseCommand):
    help = "Crea profesionales, catalogo, agenda y una reserva pagada de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reiniciar",
            action="store_true",
            help="Borra los datos de demo antes de crearlos de nuevo.",
        )

    def handle(self, *args, **opciones):
        if opciones["reiniciar"]:
            self._limpiar()

        profesional = self._crear_profesional()
        servicios = self._crear_catalogo(profesional)
        cliente = self._crear_cliente()
        # Se abren tres franjas y solo se reserva la primera: las otras dos
        # quedan libres para poder demostrar el flujo completo en vivo.
        bloques = self._abrir_agenda(profesional, cuantas=3)
        reserva = self._crear_reserva(cliente, bloques[0], servicios)
        pago = self._pagar(cliente, reserva)

        self._resumen(profesional, cliente, bloques, reserva, pago)

    # ------------------------------------------------------------------
    @transaction.atomic
    def _limpiar(self) -> None:
        Pago.objects.all().delete()
        DetalleReserva.objects.all().delete()
        Reserva.objects.all().delete()
        BloqueDisponibilidad.objects.all().delete()
        Servicio.objects.all().delete()
        Cliente.objects.all().delete()
        Profesional.objects.all().delete()
        Usuario.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING("Datos de demo eliminados."))

    def _crear_profesional(self) -> Profesional:
        existente = Profesional.objects.filter(documento="1017welder").first()
        if existente:
            return existente

        profesional = RegistroProfesionalService().registrar(
            RegistrarProfesionalCommand(
                correo="andres.plomeria@casalista.co",
                contrasena=CONTRASENA,
                nombre="Andres Ruiz - Plomeria",
                documento="1017welder",
                zonas_cobertura=("Laureles", "Belen", "Envigado"),
            )
        )
        # RN-07: sin este paso el profesional no puede recibir reservas. En
        # produccion lo hace un administrador desde el panel.
        profesional.verificado = True
        profesional.save(update_fields=["verificado"])
        return profesional

    def _crear_catalogo(self, profesional: Profesional) -> list[Servicio]:
        catalogo = [
            ("Reparacion de fuga en cocina", Decimal("85000"), 60),
            ("Cambio de sifon de lavamanos", Decimal("55000"), 45),
            ("Revision general de tuberia", Decimal("120000"), 90),
        ]
        servicios = []
        for nombre, precio, minutos in catalogo:
            servicio, _ = Servicio.objects.get_or_create(
                profesional=profesional,
                nombre=nombre,
                defaults={
                    "precio_base": precio,
                    "duracion_minutos": minutos,
                    "descripcion": "Servicio de demostracion.",
                },
            )
            servicios.append(servicio)
        return servicios

    def _crear_cliente(self) -> Cliente:
        existente = Cliente.objects.filter(usuario__username="laura@correo.com").first()
        if existente:
            return existente
        return RegistroClienteService().registrar(
            RegistrarClienteCommand(
                correo="laura@correo.com",
                contrasena=CONTRASENA,
                nombre="Laura Gomez",
                telefono="3001112233",
            )
        )

    def _abrir_agenda(
        self, profesional: Profesional, cuantas: int = 3
    ) -> list[BloqueDisponibilidad]:
        """Publica `cuantas` franjas de dos horas en dias consecutivos.

        Se busca un hueco libre antes de cada una para poder correr el comando
        varias veces sin chocar con AGD-03 (franjas solapadas).
        """
        agenda = AgendaService()
        bloques = []
        inicio = (timezone.localtime() + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        while len(bloques) < cuantas:
            ocupado = BloqueDisponibilidad.objects.filter(
                profesional=profesional,
                inicio__lt=inicio + timedelta(hours=2),
                fin__gt=inicio,
            ).exists()
            if not ocupado:
                bloques.append(
                    agenda.abrir_disponibilidad(
                        AbrirDisponibilidadCommand(
                            usuario_id=profesional.usuario_id,
                            inicio=inicio,
                            fin=inicio + timedelta(hours=2),
                        )
                    )
                )
            inicio += timedelta(days=1)
        return bloques

    def _crear_reserva(self, cliente, bloque, servicios) -> Reserva:
        return ReservaService().crear_reserva(
            CrearReservaCommand(
                usuario_id=cliente.usuario_id,
                bloque_id=bloque.pk,
                direccion="Calle 33 #70-21, apto 402",
                zona="Laureles",
                lineas=(
                    LineaSolicitada(servicio_id=servicios[0].pk, cantidad=1),
                    LineaSolicitada(servicio_id=servicios[1].pk, cantidad=1),
                ),
            )
        )

    def _pagar(self, cliente, reserva) -> Pago:
        return PagoService().procesar(
            ProcesarPagoCommand(
                usuario_id=cliente.usuario_id,
                reserva_id=reserva.pk,
                medio=Pago.Medio.TARJETA,
            )
        )

    # ------------------------------------------------------------------
    def _resumen(self, profesional, cliente, bloques, reserva, pago) -> None:
        reserva.refresh_from_db()
        self.stdout.write(self.style.SUCCESS("\nDatos de demo listos.\n"))
        self.stdout.write(f"  Profesional : {profesional.nombre} (verificado)")
        self.stdout.write(f"  Cliente     : {cliente.nombre} / {CONTRASENA}")
        self.stdout.write(f"  Correo      : {cliente.usuario.username}")
        self.stdout.write(f"  Franja      : {bloques[0]} (reservada)")
        for bloque in bloques[1:]:
            self.stdout.write(f"  Franja libre: id={bloque.pk}  {bloque}")
        self.stdout.write(
            f"  Reserva #{reserva.pk}: total $ {reserva.total} "
            f"(tarifa {reserva.tarifa_aplicada}), estado {reserva.estado}"
        )
        self.stdout.write(
            f"  Pago #{pago.pk}    : {pago.estado} por {pago.pasarela} "
            f"({pago.referencia_externa})"
        )
        self.stdout.write("\n  Token: POST /api/v1/cuentas/token/")
        self.stdout.write(
            f'        {{"username": "{cliente.usuario.username}", '
            f'"password": "{CONTRASENA}"}}\n'
        )
