"""
Pruebas de la capa de aplicacion.

Lo que se comprueba aqui NO son las reglas (esas ya se probaron contra el
Builder), sino la ORQUESTACION: que el servicio llame a quien tiene que
llamar, en el orden correcto, y que se le puedan inyectar colaboradores
distintos sin tocar variables de entorno.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalogo.dominio.excepciones import ServicioNoEncontrado
from apps.comun.dominio.excepciones import AccesoNoAutorizado
from apps.comun.pruebas import (
    NotificadorEspia,
    crear_bloque,
    crear_cliente,
    crear_profesional,
    escenario_basico,
)
from apps.cuentas.dominio.excepciones import ClienteNoRegistrado
from apps.reservas.dominio.excepciones import (
    BloqueNoEncontrado,
    BloquesSolapados,
    RangoHorarioInvalido,
    TransicionDeEstadoInvalida,
)
from apps.reservas.dominio.tarifas import TarifaBase, TarifaDinamica
from apps.reservas.dto import (
    AbrirDisponibilidadCommand,
    CancelarReservaCommand,
    CrearReservaCommand,
    LineaSolicitada,
)
from apps.reservas.models import BloqueDisponibilidad, Reserva
from apps.reservas.services import (
    AgendaService,
    CancelacionReservaService,
    ConsultaReservasService,
    ReservaService,
)


def comando_de(escenario, cantidad: int = 1, zona: str = "Laureles"):
    return CrearReservaCommand(
        usuario_id=escenario["cliente"].usuario_id,
        bloque_id=escenario["bloque"].pk,
        direccion="Calle 33 #70-21",
        zona=zona,
        lineas=(
            LineaSolicitada(servicio_id=escenario["servicio"].pk, cantidad=cantidad),
        ),
    )


class ReservaServiceTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.espia = NotificadorEspia()
        self.servicio = ReservaService(
            notificador=self.espia, calculador_tarifa=TarifaBase()
        )

    def test_crea_la_reserva_y_notifica(self):
        reserva = self.servicio.crear_reserva(comando_de(self.escenario))

        self.assertEqual(reserva.estado, Reserva.Estado.PENDIENTE)
        self.assertEqual(self.espia.avisos, [reserva.pk])

    def test_la_estrategia_de_tarifa_se_inyecta_no_se_lee_del_entorno(self):
        """Dos servicios, dos estrategias, dos totales, sin tocar settings."""
        sabado_noche = self._proximo_sabado_a_las_20()
        bloque = BloqueDisponibilidad.objects.create(
            profesional=self.escenario["profesional"],
            inicio=sabado_noche,
            fin=sabado_noche + timedelta(hours=2),
        )
        self.escenario["bloque"] = bloque

        con_recargo = ReservaService(
            notificador=NotificadorEspia(), calculador_tarifa=TarifaDinamica()
        )
        reserva = con_recargo.crear_reserva(comando_de(self.escenario))

        self.assertEqual(reserva.tarifa_aplicada, "DINAMICA")
        self.assertEqual(reserva.total, Decimal("67500.00"))

    def test_404_si_el_bloque_no_existe(self):
        comando = comando_de(self.escenario)
        inexistente = CrearReservaCommand(
            usuario_id=comando.usuario_id,
            bloque_id=999999,
            direccion=comando.direccion,
            zona=comando.zona,
            lineas=comando.lineas,
        )
        with self.assertRaises(BloqueNoEncontrado) as capturado:
            self.servicio.crear_reserva(inexistente)
        self.assertEqual(capturado.exception.estado_http, 404)

    def test_404_si_el_servicio_no_existe(self):
        comando = comando_de(self.escenario)
        inexistente = CrearReservaCommand(
            usuario_id=comando.usuario_id,
            bloque_id=comando.bloque_id,
            direccion=comando.direccion,
            zona=comando.zona,
            lineas=(LineaSolicitada(servicio_id=999999, cantidad=1),),
        )
        with self.assertRaises(ServicioNoEncontrado):
            self.servicio.crear_reserva(inexistente)

    def test_rechaza_una_cuenta_sin_perfil_de_cliente(self):
        """Un profesional autenticado no puede reservar: no es cliente."""
        profesional = crear_profesional(nombre="Sin perfil de cliente")
        comando = comando_de(self.escenario)
        ajeno = CrearReservaCommand(
            usuario_id=profesional.usuario_id,
            bloque_id=comando.bloque_id,
            direccion=comando.direccion,
            zona=comando.zona,
            lineas=comando.lineas,
        )
        with self.assertRaises(ClienteNoRegistrado):
            self.servicio.crear_reserva(ajeno)

    @staticmethod
    def _proximo_sabado_a_las_20():
        hoy = timezone.localtime()
        dias = (5 - hoy.weekday()) % 7 + 7
        return (hoy + timedelta(days=dias)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )


class AgendaServiceTest(TestCase):
    def setUp(self):
        self.profesional = crear_profesional()
        self.servicio = AgendaService()

    def _comando(self, en_horas: int = 24, duracion: int = 2):
        inicio = timezone.now() + timedelta(hours=en_horas)
        return AbrirDisponibilidadCommand(
            usuario_id=self.profesional.usuario_id,
            inicio=inicio,
            fin=inicio + timedelta(hours=duracion),
        )

    def test_publica_una_franja_libre(self):
        bloque = self.servicio.abrir_disponibilidad(self._comando())
        self.assertEqual(bloque.estado, BloqueDisponibilidad.Estado.LIBRE)

    def test_rechaza_una_franja_al_reves(self):
        inicio = timezone.now() + timedelta(hours=24)
        comando = AbrirDisponibilidadCommand(
            usuario_id=self.profesional.usuario_id,
            inicio=inicio,
            fin=inicio - timedelta(hours=1),
        )
        with self.assertRaises(RangoHorarioInvalido):
            self.servicio.abrir_disponibilidad(comando)

    def test_rechaza_franjas_solapadas(self):
        self.servicio.abrir_disponibilidad(self._comando(en_horas=24, duracion=3))
        with self.assertRaises(BloquesSolapados):
            self.servicio.abrir_disponibilidad(self._comando(en_horas=25, duracion=1))

    def test_permite_franjas_consecutivas(self):
        """De 10 a 11 y de 11 a 12 no se solapan: son seguidas."""
        self.servicio.abrir_disponibilidad(self._comando(en_horas=24, duracion=1))
        bloque = self.servicio.abrir_disponibilidad(
            self._comando(en_horas=25, duracion=1)
        )
        self.assertIsNotNone(bloque.pk)

    def test_no_muestra_franjas_que_ya_pasaron(self):
        crear_bloque(self.profesional, dentro_de_horas=-48)
        futura = crear_bloque(self.profesional, dentro_de_horas=48)

        libres = self.servicio.bloques_libres(self.profesional.pk)

        self.assertEqual([b.pk for b in libres], [futura.pk])


class CancelacionReservaServiceTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.reserva = ReservaService(
            notificador=NotificadorEspia()
        ).crear_reserva(comando_de(self.escenario))
        self.servicio = CancelacionReservaService()

    def _cancelar(self):
        return self.servicio.cancelar(
            CancelarReservaCommand(
                usuario_id=self.escenario["cliente"].usuario_id,
                reserva_id=self.reserva.pk,
            )
        )

    def test_rn04_sin_penalizacion_con_mas_de_24_horas(self):
        # El escenario basico crea la franja a 48 horas.
        reserva = self._cancelar()
        self.assertEqual(reserva.penalizacion, Decimal("0.00"))

    def test_rn04_retiene_30_por_ciento_entre_24_y_2_horas(self):
        self._mover_franja_a(horas=5)
        reserva = self._cancelar()
        self.assertEqual(reserva.penalizacion, Decimal("15000.00"))  # 30% de 50000

    def test_rn04_sin_reembolso_con_menos_de_2_horas(self):
        self._mover_franja_a(horas=1)
        reserva = self._cancelar()
        self.assertEqual(reserva.penalizacion, Decimal("50000.00"))

    def test_rn01_cancelar_libera_la_franja(self):
        self._cancelar()
        self.escenario["bloque"].refresh_from_db()
        self.assertEqual(
            self.escenario["bloque"].estado, BloqueDisponibilidad.Estado.LIBRE
        )

    def test_la_franja_liberada_se_puede_volver_a_reservar(self):
        self._cancelar()
        otro = crear_cliente(nombre="Cliente nuevo")
        escenario = {**self.escenario, "cliente": otro}

        nueva = ReservaService(notificador=NotificadorEspia()).crear_reserva(
            comando_de(escenario)
        )
        self.assertEqual(nueva.estado, Reserva.Estado.PENDIENTE)

    def test_no_se_puede_cancelar_dos_veces(self):
        self._cancelar()
        with self.assertRaises(TransicionDeEstadoInvalida) as capturado:
            self._cancelar()
        self.assertEqual(capturado.exception.estado_http, 409)

    def test_no_se_puede_cancelar_la_reserva_de_otro(self):
        intruso = crear_cliente(nombre="Intruso")
        with self.assertRaises(AccesoNoAutorizado):
            self.servicio.cancelar(
                CancelarReservaCommand(
                    usuario_id=intruso.usuario_id, reserva_id=self.reserva.pk
                )
            )

    def _mover_franja_a(self, horas: int) -> None:
        bloque = self.escenario["bloque"]
        bloque.inicio = timezone.now() + timedelta(hours=horas)
        bloque.fin = bloque.inicio + timedelta(hours=2)
        bloque.save(update_fields=["inicio", "fin"])
        self.reserva.refresh_from_db()


class ConsultaReservasServiceTest(TestCase):
    def setUp(self):
        self.escenario = escenario_basico()
        self.reserva = ReservaService(
            notificador=NotificadorEspia()
        ).crear_reserva(comando_de(self.escenario))
        self.servicio = ConsultaReservasService()

    def test_un_cliente_solo_ve_sus_reservas(self):
        otro = crear_cliente(nombre="Otro cliente")
        self.assertEqual(list(self.servicio.reservas_de(otro.usuario_id)), [])
        self.assertEqual(
            [r.pk for r in self.servicio.reservas_de(self.escenario["cliente"].usuario_id)],
            [self.reserva.pk],
        )

    def test_403_al_pedir_la_reserva_de_otro(self):
        intruso = crear_cliente(nombre="Intruso")
        with self.assertRaises(AccesoNoAutorizado) as capturado:
            self.servicio.detalle_de(intruso.usuario_id, self.reserva.pk)
        self.assertEqual(capturado.exception.estado_http, 403)
