"""
Reglas de la agenda.

Aqui viven `estaLibre()`, `ocupar()` y `seSolapaCon()`, que el diagrama de
dominio le asigna a BloqueDisponibilidad. Estan fuera del modelo porque son
decisiones de negocio, y el modelo solo persiste.

Todos los metodos son estaticos y reciben la entidad. La clase agrupa, no
guarda estado.
"""

from django.utils import timezone

from apps.reservas.dominio.excepciones import (
    BloqueNoDisponible,
    BloquesSolapados,
    RangoHorarioInvalido,
)
from apps.reservas.models import BloqueDisponibilidad, Reserva

# Un estado activo es el que sigue ocupando la agenda. Una reserva cancelada
# libera la franja (RN-01), por eso no aparece en esta tupla.
ESTADOS_QUE_OCUPAN_AGENDA = (Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA)


class ReglasAgenda:
    """Todo lo que se puede afirmar sobre una franja horaria."""

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @staticmethod
    def duracion_minutos(bloque) -> int:
        return int((bloque.fin - bloque.inicio).total_seconds() // 60)

    @staticmethod
    def esta_libre(bloque) -> bool:
        return bloque.estado == BloqueDisponibilidad.Estado.LIBRE

    @staticmethod
    def se_solapan(uno, otro) -> bool:
        """Dos franjas se pisan si cada una empieza antes de que la otra acabe.

        Se usa `<` y no `<=` a proposito: un bloque de 10:00 a 11:00 y otro de
        11:00 a 12:00 son consecutivos, no solapados.
        """
        return uno.inicio < otro.fin and otro.inicio < uno.fin

    @staticmethod
    def horas_hasta(bloque, momento=None) -> float:
        """Cuantas horas faltan para la visita. Lo necesita RN-04."""
        ahora = momento or timezone.now()
        return (bloque.inicio - ahora).total_seconds() / 3600

    # ------------------------------------------------------------------
    # Exigencias (lanzan si no se cumplen)
    # ------------------------------------------------------------------
    @classmethod
    def exigir_rango_valido(cls, inicio, fin) -> None:
        if fin <= inicio:
            raise RangoHorarioInvalido(
                "La franja debe terminar despues de empezar.",
                inicio=inicio.isoformat(),
                fin=fin.isoformat(),
            )

    @classmethod
    def exigir_sin_solapamiento(cls, profesional, inicio, fin) -> None:
        """Un profesional no puede estar en dos visitas a la vez.

        La consulta compara con lo que ya esta publicado. No se puede expresar
        como restriccion de base de datos portable, asi que se valida aqui y
        se documenta la limitacion.
        """
        hay_choque = BloqueDisponibilidad.objects.filter(
            profesional=profesional, inicio__lt=fin, fin__gt=inicio
        ).exists()
        if hay_choque:
            raise BloquesSolapados(
                "El profesional ya tiene una franja publicada en ese horario.",
                inicio=inicio.isoformat(),
                fin=fin.isoformat(),
            )

    @classmethod
    def exigir_disponible(cls, bloque) -> None:
        """RN-01: la franja tiene que estar libre y sin reserva activa.

        Se comprueban las dos cosas y no solo el estado porque son fuentes
        distintas: el campo `estado` es el resumen y la tabla de reservas es
        la verdad. Si alguna vez se desincronizan, esta doble verificacion lo
        detecta en lugar de vender dos veces la misma franja.
        """
        if not cls.esta_libre(bloque):
            raise BloqueNoDisponible(
                "La franja horaria ya fue tomada.", bloque_id=bloque.pk
            )
        ya_reservado = Reserva.objects.filter(
            bloque=bloque, estado__in=ESTADOS_QUE_OCUPAN_AGENDA
        ).exists()
        if ya_reservado:
            raise BloqueNoDisponible(
                "La franja horaria ya tiene una reserva activa.", bloque_id=bloque.pk
            )

    # ------------------------------------------------------------------
    # Transiciones (cambian el objeto en memoria; guardar es de quien llama)
    # ------------------------------------------------------------------
    @staticmethod
    def ocupar(bloque) -> None:
        bloque.estado = BloqueDisponibilidad.Estado.OCUPADO

    @staticmethod
    def liberar(bloque) -> None:
        bloque.estado = BloqueDisponibilidad.Estado.LIBRE
