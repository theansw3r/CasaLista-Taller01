"""
Middleware de correlacion de peticiones.

Cuando la aplicacion vive detras de un API Gateway, una peticion del cliente
atraviesa varios procesos antes de llegar aqui. Para poder seguirle el rastro
en los logs, el Gateway inyecta una cabecera `X-Request-ID` y todos los
servicios de la cadena la repiten.

Este middleware hace dos cosas:

1. Si la cabecera no llega (por ejemplo, en desarrollo sin Gateway), genera
   un identificador nuevo, para que el resto del codigo siempre tenga uno.
2. Lo devuelve en la respuesta, que es lo que permite a quien reporta un error
   pegar el identificador y que nosotros encontremos exactamente esa peticion.
"""

import uuid

CABECERA_ENTRADA = "HTTP_X_REQUEST_ID"
CABECERA_SALIDA = "X-Request-ID"


class IdentificadorDePeticionMiddleware:
    """Garantiza que toda peticion tenga un identificador de correlacion."""

    def __init__(self, siguiente):
        self.siguiente = siguiente

    def __call__(self, request):
        request.id_peticion = request.META.get(CABECERA_ENTRADA) or uuid.uuid4().hex
        respuesta = self.siguiente(request)
        respuesta[CABECERA_SALIDA] = request.id_peticion
        return respuesta
