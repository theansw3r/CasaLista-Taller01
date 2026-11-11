from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Servicio
from apps.cuentas.dto import RegistrarClienteCommand, RegistrarProfesionalCommand
from apps.cuentas.models import Cliente, Profesional
from apps.cuentas.services import (
    RegistroClienteService,
    RegistroProfesionalService,
    VerificacionProfesionalService,
)
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

# Cada profesional trae su catalogo. Son dos oficios distintos a proposito:
# asi se puede demostrar el filtro por oficio en la sustentacion.
PROFESIONALES = [
    {
        "correo": "andres.plomeria@casalista.co",
        "nombre": "Andres Ruiz - Plomeria",
        "documento": "1017welder",
        "descripcion": (
            "Plomero con 12 anos de experiencia en reparacion de fugas, "
            "instalacion sanitaria y redes hidraulicas de vivienda."
        ),
        "zonas": ("Laureles", "Belen", "Envigado"),
        "hora": 9,
        "catalogo": [
            (
                Servicio.Oficio.PLOMERIA,
                "Reparacion de fuga en cocina",
                "Deteccion y reparacion de fugas en tuberia de cocina. Incluye "
                "materiales basicos y prueba de estanqueidad.",
                Decimal("85000"),
                60,
            ),
            (
                Servicio.Oficio.PLOMERIA,
                "Cambio de sifon de lavamanos",
                "Retiro del sifon antiguo e instalacion de uno nuevo, con "
                "sellado y verificacion de drenaje.",
                Decimal("55000"),
                60,
            ),
            (
                Servicio.Oficio.PLOMERIA,
                "Revision general de tuberia",
                "Inspeccion completa de la red hidraulica del apartamento con "
                "informe de hallazgos y recomendaciones.",
                Decimal("120000"),
                120,
            ),
        ],
    },
    {
        "correo": "carolina.electricidad@casalista.co",
        "nombre": "Carolina Mesa - Electricidad",
        "documento": "43876512",
        "descripcion": (
            "Tecnica electricista certificada. Instalaciones residenciales, "
            "tableros de control y diagnostico de cortos."
        ),
        "zonas": ("Laureles", "Sabaneta"),
        "hora": 14,
        "catalogo": [
            (
                Servicio.Oficio.ELECTRICIDAD,
                "Instalacion de lampara de techo",
                "Montaje e instalacion electrica de lampara, incluye puesta a "
                "tierra y prueba de encendido.",
                Decimal("70000"),
                60,
            ),
            (
                Servicio.Oficio.ELECTRICIDAD,
                "Revision de tablero electrico",
                "Diagnostico completo del tablero, revision de breakers y "
                "medicion de cargas por circuito.",
                Decimal("95000"),
                90,
            ),
            (
                Servicio.Oficio.ELECTRODOMESTICOS,
                "Reparacion de lavadora",
                "Diagnostico y reparacion de lavadora que no centrifuga o no "
                "drena. No incluye repuestos.",
                Decimal("110000"),
                120,
            ),
        ],
    },
]

# Cuantas franjas abre cada profesional y cuantas se dejan sin reservar.
FRANJAS_POR_PROFESIONAL = 6


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

        cliente = self._crear_cliente()
        creados = []

        for datos in PROFESIONALES:
            profesional = self._crear_profesional(datos)
            servicios = self._crear_catalogo(profesional, datos["catalogo"])
            bloques = self._abrir_agenda(profesional, datos["hora"])
            creados.append((profesional, servicios, bloques))

        # Solo el primero recibe una reserva ya pagada, como ejemplo. Los demas
        # horarios quedan libres para poder reservar en vivo.
        profesional, servicios, bloques = creados[0]
        reserva = self._crear_reserva(cliente, bloques[0], servicios)
        pago = self._pagar(cliente, reserva)

        self._resumen(cliente, creados, reserva, pago)

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

    def _crear_profesional(self, datos: dict) -> Profesional:
        existente = Profesional.objects.filter(documento=datos["documento"]).first()
        if existente:
            profesional = existente
        else:
            profesional = RegistroProfesionalService().registrar(
                RegistrarProfesionalCommand(
                    correo=datos["correo"],
                    contrasena=CONTRASENA,
                    nombre=datos["nombre"],
                    documento=datos["documento"],
                    descripcion=datos["descripcion"],
                    zonas_cobertura=datos["zonas"],
                )
            )

        # RN-07: sin verificar no aparece en las busquedas. En produccion lo
        # hace un administrador desde el panel.
        VerificacionProfesionalService().verificar(
            Profesional.objects.filter(pk=profesional.pk)
        )
        profesional.refresh_from_db()
        return profesional

    def _crear_catalogo(self, profesional: Profesional, catalogo) -> list[Servicio]:
        servicios = []
        for categoria, nombre, descripcion, precio, minutos in catalogo:
            servicio, _ = Servicio.objects.get_or_create(
                profesional=profesional,
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "precio_base": precio,
                    "duracion_minutos": minutos,
                    "descripcion": descripcion,
                },
            )
            servicios.append(servicio)
        return servicios

    def _abrir_agenda(
        self, profesional: Profesional, hora: int
    ) -> list[BloqueDisponibilidad]:
        """Deja al profesional con FRANJAS_POR_PROFESIONAL huecos libres.

        Cuenta las que ya tiene libres, para que correr el comando varias veces
        no llene la agenda de franjas repetidas.
        """
        agenda = AgendaService()
        libres = list(
            BloqueDisponibilidad.objects.filter(
                profesional=profesional,
                estado=BloqueDisponibilidad.Estado.LIBRE,
                inicio__gte=timezone.now(),
            ).order_by("inicio")
        )

        inicio = (timezone.localtime() + timedelta(days=1)).replace(
            hour=hora, minute=0, second=0, microsecond=0
        )
        while len(libres) < FRANJAS_POR_PROFESIONAL:
            ocupado = BloqueDisponibilidad.objects.filter(
                profesional=profesional,
                inicio__lt=inicio + timedelta(hours=2),
                fin__gt=inicio,
            ).exists()
            if not ocupado:
                libres.append(
                    agenda.abrir_disponibilidad(
                        AbrirDisponibilidadCommand(
                            usuario_id=profesional.usuario_id,
                            inicio=inicio,
                            fin=inicio + timedelta(hours=2),
                        )
                    )
                )
            inicio += timedelta(days=1)

        return sorted(libres, key=lambda b: b.inicio)

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

    def _resumen(self, cliente, creados, reserva, pago) -> None:
        reserva.refresh_from_db()
        self.stdout.write(self.style.SUCCESS("\nDatos de demo listos.\n"))

        self.stdout.write(f"  Cliente: {cliente.nombre}")
        self.stdout.write(f"    {cliente.usuario.username} / {CONTRASENA}\n")

        for profesional, servicios, bloques in creados:
            libres = [b for b in bloques if b.estado == BloqueDisponibilidad.Estado.LIBRE]
            self.stdout.write(f"  {profesional.nombre} (verificado)")
            self.stdout.write(f"    {profesional.usuario.username} / {CONTRASENA}")
            self.stdout.write(f"    {len(servicios)} servicios")
            self.stdout.write(f"    zonas: {profesional.zonas_cobertura}")
            self.stdout.write(f"    franjas libres: {len(libres)}")
            for bloque in libres[:3]:
                self.stdout.write(f"      - {bloque}")
            if len(libres) > 3:
                self.stdout.write(f"      ... y {len(libres) - 3} mas\n")
            else:
                self.stdout.write("")

        self.stdout.write(
            f"  Reserva #{reserva.pk} de ejemplo: $ {reserva.total} "
            f"({reserva.estado}), pago {pago.estado}\n"
        )
