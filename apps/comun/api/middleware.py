import uuid

CABECERA_ENTRADA = "HTTP_X_REQUEST_ID"
CABECERA_SALIDA = "X-Request-ID"


class IdentificadorDePeticionMiddleware:

    def __init__(self, siguiente):
        self.siguiente = siguiente

    def __call__(self, request):
        request.id_peticion = request.META.get(CABECERA_ENTRADA) or uuid.uuid4().hex
        respuesta = self.siguiente(request)
        respuesta[CABECERA_SALIDA] = request.id_peticion
        return respuesta
