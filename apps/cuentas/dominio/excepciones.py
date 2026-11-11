from django.utils.translation import gettext_lazy as _lazy

from apps.comun.dominio.excepciones import (
    DatosInvalidos,
    RecursoNoEncontrado,
    ReglaDeNegocioViolada,
)


class CorreoYaRegistrado(DatosInvalidos):

    codigo = "CTA-01"
    mensaje_por_defecto = _lazy("Ya existe una cuenta registrada con ese correo.")


class DocumentoYaRegistrado(DatosInvalidos):

    codigo = "CTA-04"
    mensaje_por_defecto = _lazy("Ya existe un profesional con ese documento.")


class ClienteNoRegistrado(RecursoNoEncontrado):

    codigo = "CTA-02"
    mensaje_por_defecto = _lazy("La cuenta autenticada no tiene un perfil de cliente.")


class ProfesionalNoRegistrado(RecursoNoEncontrado):

    codigo = "CTA-03"
    mensaje_por_defecto = _lazy("La cuenta autenticada no tiene un perfil de profesional.")


class ProfesionalNoHabilitado(ReglaDeNegocioViolada):

    codigo = "RN-07"
    mensaje_por_defecto = _lazy("El profesional no está habilitado para esta reserva.")
