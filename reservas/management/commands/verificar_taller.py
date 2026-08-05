"""
Recorrido guiado para verificar en vivo lo que pide la rubrica del Taller 01.

    python manage.py verificar_taller

No es parte de la app: es una herramienta de demostracion que ejercita el
Builder, las Factories y el Service (via HTTP real, con django.test.Client)
usando datos propios, sin afectar los que ya tengas.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.test import Client
from django.utils import timezone

from ...domain.excepciones import ReglaDeNegocioViolada
from ...domain.reserva_builder import ReservaBuilder
from ...infra.factories import CalculadorTarifaFactory, NotificadorFactory
from ...models import BloqueDisponibilidad, Cliente, Profesional, Reserva, Servicio


class Command(BaseCommand):
    help = "Recorrido guiado: prueba el Builder, la Factory y el Service en vivo."

    def handle(self, *args, **opciones):
        cliente, profesional, servicio = self._preparar_datos()

        self._titulo("1. BUILDER - invariantes de la Reserva (domain/reserva_builder.py)")
        self._probar_builder_valido(cliente, profesional, servicio)
        self._probar_builder_rn07(cliente, profesional, servicio)
        self._probar_builder_rn01(cliente, profesional, servicio)

        self._titulo("2. FACTORY - implementacion segun el entorno (infra/factories.py)")
        self._probar_factories()

        self._titulo("3. SERVICE + VISTA - flujo HTTP completo (services.py + views.py)")
        self._probar_endpoint_http(cliente, profesional, servicio)

        self._titulo("Listo")
        self.stdout.write(
            f"Entra a http://127.0.0.1:8000/mis-reservas/ logueado como "
            f"'{cliente.usuario.username}' (password: clave-de-verificacion) "
            f"para ver las reservas que se crearon aqui."
        )

    # ------------------------------------------------------------------
    def _titulo(self, texto):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(texto))
        self.stdout.write("-" * len(texto))

    def _preparar_datos(self):
        usuario_cliente, creado = User.objects.get_or_create(
            username="verificacion@casalista.co",
            defaults={"email": "verificacion@casalista.co"},
        )
        if creado:
            usuario_cliente.set_password("clave-de-verificacion")
            usuario_cliente.save()
        cliente, _ = Cliente.objects.get_or_create(
            usuario=usuario_cliente,
            defaults={"nombre": "Cliente de Verificacion", "telefono": "3000000000"},
        )

        usuario_pro, _ = User.objects.get_or_create(
            username="profesional-verificacion@casalista.co",
            defaults={"email": "profesional-verificacion@casalista.co"},
        )
        profesional, _ = Profesional.objects.get_or_create(
            usuario=usuario_pro,
            defaults={
                "nombre": "Profesional de Verificacion",
                "verificado": True,
                "zonas_cobertura": "Laureles,Belen",
            },
        )
        servicio, _ = Servicio.objects.get_or_create(
            profesional=profesional,
            nombre="Servicio de prueba",
            defaults={"precio_base": Decimal("50000"), "duracion_minutos": 60},
        )
        return cliente, profesional, servicio

    def _bloque_nuevo(self, profesional, dias_desde_hoy):
        inicio = timezone.now() + timedelta(days=dias_desde_hoy)
        return BloqueDisponibilidad.objects.create(
            profesional=profesional, inicio=inicio, fin=inicio + timedelta(hours=2)
        )

    # --- 1. Builder ------------------------------------------------------
    def _probar_builder_valido(self, cliente, profesional, servicio):
        bloque = self._bloque_nuevo(profesional, 10)
        reserva = (
            ReservaBuilder()
            .para_cliente(cliente)
            .en_bloque(bloque)
            .en_direccion("Calle 30 #45-12", "Laureles")
            .agregar_servicio(servicio, 1)
            .build()
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  OK  build() valido -> Reserva #{reserva.pk}, total=$ {reserva.total}"
            )
        )
        self.stdout.write(f"      el bloque #{bloque.pk} paso a estado: {reserva.bloque.estado}")

    def _probar_builder_rn07(self, cliente, profesional, servicio):
        bloque = self._bloque_nuevo(profesional, 11)
        try:
            (
                ReservaBuilder()
                .para_cliente(cliente)
                .en_bloque(bloque)
                .en_direccion("Calle 1", "Sabaneta")  # el profesional no cubre Sabaneta
                .agregar_servicio(servicio, 1)
                .build()
            )
            self.stdout.write(self.style.ERROR("  FALLO: debia rechazar la zona y no lo hizo"))
        except ReglaDeNegocioViolada as error:
            self.stdout.write(
                self.style.WARNING(f"  OK  RN-07 rechazada como se esperaba -> {error.codigo}: {error}")
            )
        bloque.refresh_from_db()
        estado = "LIBRE (correcto, no se guardo nada)" if bloque.esta_libre() else "OCUPADO (mal)"
        self.stdout.write(f"      el bloque #{bloque.pk} quedo: {estado}")

    def _probar_builder_rn01(self, cliente, profesional, servicio):
        bloque = self._bloque_nuevo(profesional, 12)
        (
            ReservaBuilder()
            .para_cliente(cliente)
            .en_bloque(bloque)
            .en_direccion("Calle 30", "Laureles")
            .agregar_servicio(servicio, 1)
            .build()
        )
        try:
            (
                ReservaBuilder()
                .para_cliente(cliente)
                .en_bloque(bloque)  # ya quedo ocupado en la linea anterior
                .en_direccion("Calle 30", "Laureles")
                .agregar_servicio(servicio, 1)
                .build()
            )
            self.stdout.write(self.style.ERROR("  FALLO: debia rechazar el bloque duplicado"))
        except ReglaDeNegocioViolada as error:
            self.stdout.write(
                self.style.WARNING(f"  OK  RN-01 rechazada como se esperaba -> {error.codigo}: {error}")
            )

    # --- 2. Factory --------------------------------------------------------
    def _probar_factories(self):
        self.stdout.write(f"  NOTIFICADOR_TYPE actual (entorno) -> {type(NotificadorFactory.crear()).__name__}")
        self.stdout.write(f"  TARIFA_TYPE actual (entorno)      -> {type(CalculadorTarifaFactory.crear()).__name__}")
        self.stdout.write("")
        self.stdout.write("  Sin tocar el entorno, pidiendole el otro valor a la misma Factory:")
        self.stdout.write(
            f"    NotificadorFactory.crear('REAL') -> {type(NotificadorFactory.crear('REAL')).__name__}"
        )
        self.stdout.write(
            f"    NotificadorFactory.crear('MOCK') -> {type(NotificadorFactory.crear('MOCK')).__name__}"
        )
        self.stdout.write(
            f"    CalculadorTarifaFactory.crear('DINAMICA') -> "
            f"{type(CalculadorTarifaFactory.crear('DINAMICA')).__name__}"
        )
        self.stdout.write("")
        self.stdout.write(
            "  Para verlo cambiar por la VARIABLE DE ENTORNO (lo que pide la rubrica), "
            "sal de aqui y corre:\n"
            '    $env:NOTIFICADOR_TYPE="REAL"; $env:TARIFA_TYPE="DINAMICA"; python manage.py sembrar_demo'
        )

    # --- 3. HTTP -------------------------------------------------------------
    def _probar_endpoint_http(self, cliente, profesional, servicio):
        # SERVER_NAME="localhost": Client() manda Host: testserver por defecto,
        # que no esta en ALLOWED_HOSTS fuera del test runner.
        navegador_simulado = Client(SERVER_NAME="localhost")
        navegador_simulado.force_login(cliente.usuario)

        bloque = self._bloque_nuevo(profesional, 13)
        payload = {
            "bloque_id": bloque.pk,
            "direccion": "Calle 30 #45-12",
            "zona": "Laureles",
            "servicios": [{"servicio_id": servicio.pk, "cantidad": 1}],
        }

        respuesta = navegador_simulado.post(
            "/api/reservas/", data=payload, content_type="application/json"
        )
        self.stdout.write(f"  POST /api/reservas/ (primera vez)  -> {respuesta.status_code}")
        self.stdout.write(f"      {respuesta.json()}")

        respuesta_repetida = navegador_simulado.post(
            "/api/reservas/", data=payload, content_type="application/json"
        )
        self.stdout.write(f"  POST /api/reservas/ (mismo bloque) -> {respuesta_repetida.status_code}")
        self.stdout.write(f"      {respuesta_repetida.json()}")

        sin_login = Client(SERVER_NAME="localhost").post(
            "/api/reservas/", data=payload, content_type="application/json"
        )
        self.stdout.write(f"  POST /api/reservas/ (sin login)    -> {sin_login.status_code}")
