from django.utils.translation import gettext as _, gettext_lazy as _lazy
from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


class DatosDeReservaIncompletos(DatosInvalidos):
    codigo = "RES-01"
    mensaje_por_defecto = _lazy("Faltan datos obligatorios para construir la reserva.")


class ReservaSinServicios(DatosInvalidos):
    codigo = "RES-02"
    mensaje_por_defecto = _lazy("La reserva debe incluir al menos un servicio.")


class CantidadInvalida(DatosInvalidos):
    codigo = "RES-03"
    mensaje_por_defecto = _lazy("La cantidad de un servicio debe ser mayor que cero.")


class RangoHorarioInvalido(DatosInvalidos):
    codigo = "AGD-01"
    mensaje_por_defecto = _lazy("La franja debe terminar despues de empezar.")


class BloqueNoEncontrado(RecursoNoEncontrado):
    codigo = "AGD-02"
    mensaje_por_defecto = _lazy("La franja horaria solicitada no existe.")


class ReservaNoEncontrada(RecursoNoEncontrado):
    codigo = "RES-04"
    mensaje_por_defecto = _lazy("La reserva solicitada no existe.")


class BloqueNoDisponible(ReglaDeNegocioViolada):

    codigo = "RN-01"
    mensaje_por_defecto = _lazy("La franja horaria ya fue tomada.")


class BloqueDeOtroProfesional(ReglaDeNegocioViolada):

    codigo = "RN-01"
    mensaje_por_defecto = _lazy("La franja pertenece a otro profesional.")


class ServiciosDeDistintosProfesionales(ReglaDeNegocioViolada):

    codigo = "RN-02"
    mensaje_por_defecto = (
        _lazy("Todos los servicios de una reserva deben ser del mismo profesional.")
    )


class DuracionExcedeBloque(ReglaDeNegocioViolada):

    codigo = "RN-01b"
    mensaje_por_defecto = _lazy("Los servicios no caben en la franja elegida.")


class BloquesSolapados(ReglaDeNegocioViolada):

    codigo = "AGD-03"
    mensaje_por_defecto = _lazy("La franja se solapa con otra ya publicada.")


class TransicionDeEstadoInvalida(ReglaDeNegocioViolada):

    codigo = "RES-05"
    mensaje_por_defecto = _lazy("La reserva no admite esa operacion en su estado actual.")
