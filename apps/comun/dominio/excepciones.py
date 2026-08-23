"""
Excepciones base del dominio.

La idea es que el dominio hable en su propio idioma ("este bloque ya esta
tomado") y que un unico traductor, en la capa de API, convierta ese idioma a
HTTP. Por eso cada excepcion sabe DOS cosas de si misma:

* `codigo`: el identificador de la regla que se violo (RN-01, RN-02...). Es el
  mismo codigo del Business Case, asi que un error en produccion se puede
  rastrear hasta el documento de negocio.
* `estado_http`: el codigo de estado que le corresponde.

Ninguna vista necesita saber esto: el manejador de errores de DRF lee los dos
atributos y arma la respuesta.
"""


class ErrorDeDominio(Exception):
    """Raiz de todos los errores esperados del negocio.

    "Esperado" quiere decir que NO es un bug: es una situacion que el negocio
    contempla (una franja ocupada, un profesional sin verificar). Los bugs
    siguen subiendo como excepciones normales y terminan en un 500.
    """

    codigo = "ERR-000"
    estado_http = 409
    mensaje_por_defecto = "La operacion viola una regla de negocio."

    def __init__(self, mensaje: str = "", **contexto) -> None:
        super().__init__(mensaje or self.mensaje_por_defecto)
        # Datos extra utiles para el cliente de la API (por ejemplo, cuantos
        # minutos sobran). Nunca se ponen aqui detalles internos del sistema.
        self.contexto = contexto

    def como_diccionario(self) -> dict:
        cuerpo = {"codigo": self.codigo, "mensaje": str(self)}
        if self.contexto:
            cuerpo["contexto"] = self.contexto
        return cuerpo


class ReglaDeNegocioViolada(ErrorDeDominio):
    """Conflicto con el estado actual del sistema. Se traduce a 409.

    Se usa cuando la peticion esta bien formada pero choca con la realidad:
    la franja ya se ocupo, la reserva ya se pago, el profesional no cubre la
    zona. Reintentar con los mismos datos volveria a fallar.
    """

    codigo = "RN-000"
    estado_http = 409


class DatosInvalidos(ErrorDeDominio):
    """La peticion esta mal formada o es incoherente. Se traduce a 400."""

    codigo = "VAL-000"
    estado_http = 400


class RecursoNoEncontrado(ErrorDeDominio):
    """El identificador recibido no corresponde a nada. Se traduce a 404."""

    codigo = "VAL-404"
    estado_http = 404
    mensaje_por_defecto = "El recurso solicitado no existe."


class AccesoNoAutorizado(ErrorDeDominio):
    """El usuario esta autenticado pero el recurso no es suyo. Se traduce a 403."""

    codigo = "VAL-403"
    estado_http = 403
    mensaje_por_defecto = "No tiene permiso sobre este recurso."
