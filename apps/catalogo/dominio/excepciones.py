"""Errores de negocio del modulo Catalogo."""

from apps.comun.dominio.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada


class ServicioNoEncontrado(RecursoNoEncontrado):
    codigo = "CAT-01"
    mensaje_por_defecto = "El servicio solicitado no existe."


class ProfesionalNoEncontrado(RecursoNoEncontrado):
    codigo = "CAT-02"
    mensaje_por_defecto = "El profesional solicitado no existe."


class ServicioInactivo(ReglaDeNegocioViolada):
    """El servicio existe pero el profesional lo dio de baja."""

    codigo = "CAT-03"
    mensaje_por_defecto = "El servicio ya no esta disponible."
