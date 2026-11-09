from django.utils.translation import gettext as _, gettext_lazy as _lazy
from apps.comun.dominio.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada


class ServicioNoEncontrado(RecursoNoEncontrado):
    codigo = "CAT-01"
    mensaje_por_defecto = _lazy("El servicio solicitado no existe.")


class ProfesionalNoEncontrado(RecursoNoEncontrado):
    codigo = "CAT-02"
    mensaje_por_defecto = _lazy("El profesional solicitado no existe.")


class ServicioInactivo(ReglaDeNegocioViolada):

    codigo = "CAT-03"
    mensaje_por_defecto = _lazy("El servicio ya no esta disponible.")


class ServicioDuplicado(ReglaDeNegocioViolada):
    codigo = "CAT-04"
    mensaje_por_defecto = _lazy("Ya publicaste un servicio con ese nombre.")


class ServicioFueraDeEstandar(ReglaDeNegocioViolada):
    """El servicio no cumple el nicho definido en el Business Case (1.1)."""

    codigo = "CAT-05"
    estado_http = 400
    mensaje_por_defecto = _lazy("El servicio no cumple los estandares de CasaLista.")
