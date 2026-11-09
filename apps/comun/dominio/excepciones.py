from django.utils.translation import gettext as _, gettext_lazy as _lazy
class ErrorDeDominio(Exception):

    codigo = "ERR-000"
    estado_http = 409
    mensaje_por_defecto = _lazy("La operacion viola una regla de negocio.")

    def __init__(self, mensaje: str = "", **contexto) -> None:
        super().__init__(mensaje or self.mensaje_por_defecto)
        self.contexto = contexto

    def como_diccionario(self) -> dict:
        cuerpo = {"codigo": self.codigo, "mensaje": str(self)}
        if self.contexto:
            cuerpo["contexto"] = self.contexto
        return cuerpo


class ReglaDeNegocioViolada(ErrorDeDominio):

    codigo = "RN-000"
    estado_http = 409


class DatosInvalidos(ErrorDeDominio):

    codigo = "VAL-000"
    estado_http = 400


class RecursoNoEncontrado(ErrorDeDominio):

    codigo = "VAL-404"
    estado_http = 404
    mensaje_por_defecto = _lazy("El recurso solicitado no existe.")


class AccesoNoAutorizado(ErrorDeDominio):

    codigo = "VAL-403"
    estado_http = 403
    mensaje_por_defecto = _lazy("No tiene permiso sobre este recurso.")
