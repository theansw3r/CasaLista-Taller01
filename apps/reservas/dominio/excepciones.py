"""
Errores de negocio del modulo Agenda y Reservas.

El `codigo` de cada clase es el mismo de la tabla de reglas del Business Case
(seccion 1.8). Esa correspondencia es intencional: cuando un cliente reporta
"me sale RN-01", el codigo se busca en el documento de negocio y se sabe
exactamente que regla se aplico, sin leer una linea de Python.
"""

from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


# --- Datos incompletos o incoherentes (400) --------------------------------
class DatosDeReservaIncompletos(DatosInvalidos):
    codigo = "RES-01"
    mensaje_por_defecto = "Faltan datos obligatorios para construir la reserva."


class ReservaSinServicios(DatosInvalidos):
    codigo = "RES-02"
    mensaje_por_defecto = "La reserva debe incluir al menos un servicio."


class CantidadInvalida(DatosInvalidos):
    codigo = "RES-03"
    mensaje_por_defecto = "La cantidad de un servicio debe ser mayor que cero."


class RangoHorarioInvalido(DatosInvalidos):
    codigo = "AGD-01"
    mensaje_por_defecto = "La franja debe terminar despues de empezar."


# --- Recursos inexistentes (404) -------------------------------------------
class BloqueNoEncontrado(RecursoNoEncontrado):
    codigo = "AGD-02"
    mensaje_por_defecto = "La franja horaria solicitada no existe."


class ReservaNoEncontrada(RecursoNoEncontrado):
    codigo = "RES-04"
    mensaje_por_defecto = "La reserva solicitada no existe."


# --- Conflictos con el estado del sistema (409) ----------------------------
class BloqueNoDisponible(ReglaDeNegocioViolada):
    """RN-01: un bloque solo puede tener una reserva activa."""

    codigo = "RN-01"
    mensaje_por_defecto = "La franja horaria ya fue tomada."


class BloqueDeOtroProfesional(ReglaDeNegocioViolada):
    """RN-01: la agenda reservada debe ser la del profesional que atiende."""

    codigo = "RN-01"
    mensaje_por_defecto = "La franja pertenece a otro profesional."


class ServiciosDeDistintosProfesionales(ReglaDeNegocioViolada):
    """RN-02: todos los servicios de una reserva son del mismo profesional."""

    codigo = "RN-02"
    mensaje_por_defecto = (
        "Todos los servicios de una reserva deben ser del mismo profesional."
    )


class DuracionExcedeBloque(ReglaDeNegocioViolada):
    """Derivada de RN-01: lo reservado tiene que caber en la franja."""

    codigo = "RN-01b"
    mensaje_por_defecto = "Los servicios no caben en la franja elegida."


class BloquesSolapados(ReglaDeNegocioViolada):
    """Un profesional no puede publicar dos franjas que se pisen."""

    codigo = "AGD-03"
    mensaje_por_defecto = "La franja se solapa con otra ya publicada."


class TransicionDeEstadoInvalida(ReglaDeNegocioViolada):
    """Se intento un cambio de estado que el ciclo de vida no permite."""

    codigo = "RES-05"
    mensaje_por_defecto = "La reserva no admite esa operacion en su estado actual."
