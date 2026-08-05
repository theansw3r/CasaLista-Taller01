"""
Excepciones de dominio.

Toda la aplicacion lanza subclases de `ReglaDeNegocioViolada`. Gracias a eso
la vista necesita un unico `except` y sigue sin conocer las reglas: solo lee
`codigo` y `estado_http` del error.
"""


class ReglaDeNegocioViolada(Exception):
    """Error de negocio esperado (no es un bug)."""

    codigo = "RN-00"
    estado_http = 409

    def como_respuesta(self) -> dict:
        """Representacion serializable del error, sin filtrar detalles internos."""
        return {"codigo": self.codigo, "error": str(self)}


# --- Validaciones estructurales de la peticion ------------------------------


class DatosIncompletos(ReglaDeNegocioViolada):
    codigo = "VAL-01"
    estado_http = 422


class ReservaSinServicios(ReglaDeNegocioViolada):
    codigo = "VAL-02"
    estado_http = 422


class CantidadInvalida(ReglaDeNegocioViolada):
    codigo = "VAL-03"
    estado_http = 422


class ServicioInactivo(ReglaDeNegocioViolada):
    codigo = "VAL-04"
    estado_http = 422


class RecursoInexistente(ReglaDeNegocioViolada):
    codigo = "VAL-05"
    estado_http = 404


class ClienteNoRegistrado(ReglaDeNegocioViolada):
    codigo = "VAL-06"
    estado_http = 403


# --- Reglas del Business Case (seccion 1.8) ---------------------------------


class BloqueNoDisponible(ReglaDeNegocioViolada):
    """RN-01: un bloque solo puede tener una reserva activa."""

    codigo = "RN-01"


class BloqueDeOtroProfesional(ReglaDeNegocioViolada):
    """RN-01: la agenda reservada debe ser la del profesional que atiende."""

    codigo = "RN-01"


class ServiciosDeDistintosProfesionales(ReglaDeNegocioViolada):
    """RN-02: todos los servicios de una reserva son del mismo profesional."""

    codigo = "RN-02"


class ProfesionalNoHabilitado(ReglaDeNegocioViolada):
    """RN-07: el profesional debe estar verificado y cubrir la zona."""

    codigo = "RN-07"


class DuracionExcedeBloque(ReglaDeNegocioViolada):
    """RN-08 (derivada): los servicios deben caber en la franja reservada."""

    codigo = "RN-08"
