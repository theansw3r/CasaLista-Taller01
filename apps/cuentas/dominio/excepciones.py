from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


class CorreoYaRegistrado(DatosInvalidos):

    codigo = "CTA-01"
    mensaje_por_defecto = "Ya existe una cuenta registrada con ese correo."


class ClienteNoRegistrado(RecursoNoEncontrado):

    codigo = "CTA-02"
    mensaje_por_defecto = "La cuenta autenticada no tiene un perfil de cliente."


class ProfesionalNoRegistrado(RecursoNoEncontrado):

    codigo = "CTA-03"
    mensaje_por_defecto = "La cuenta autenticada no tiene un perfil de profesional."


class ProfesionalNoHabilitado(ReglaDeNegocioViolada):

    codigo = "RN-07"
    mensaje_por_defecto = "El profesional no esta habilitado para esta reserva."
