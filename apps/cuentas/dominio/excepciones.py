"""Errores de negocio del modulo Cuentas."""

from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


class CorreoYaRegistrado(DatosInvalidos):
    """Dos cuentas no pueden compartir correo."""

    codigo = "CTA-01"
    mensaje_por_defecto = "Ya existe una cuenta registrada con ese correo."


class ClienteNoRegistrado(RecursoNoEncontrado):
    """La cuenta esta autenticada pero no tiene perfil de cliente."""

    codigo = "CTA-02"
    mensaje_por_defecto = "La cuenta autenticada no tiene un perfil de cliente."


class ProfesionalNoRegistrado(RecursoNoEncontrado):
    """La cuenta esta autenticada pero no tiene perfil de profesional."""

    codigo = "CTA-03"
    mensaje_por_defecto = "La cuenta autenticada no tiene un perfil de profesional."


class ProfesionalNoHabilitado(ReglaDeNegocioViolada):
    """RN-07: el profesional debe estar verificado y cubrir la zona del cliente."""

    codigo = "RN-07"
    mensaje_por_defecto = "El profesional no esta habilitado para esta reserva."
