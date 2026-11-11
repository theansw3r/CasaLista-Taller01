from django.utils.translation import gettext_lazy as _lazy

from apps.comun.dominio.excepciones import ErrorDeDominio


class ProveedorNoDisponible(ErrorDeDominio):
    """El tercero no respondio o respondio algo que no se puede usar.

    503 y no 502: para quien llama a CasaLista lo que importa es que el dato
    no esta disponible ahora, y que puede seguir con la reserva sin el.
    """

    codigo = "INT-503"
    estado_http = 503
    mensaje_por_defecto = _lazy(
        "El clima no está disponible. Puedes continuar tu reserva."
    )


class AliadoNoConfigurado(ErrorDeDominio):
    codigo = "ALIADO-PENDIENTE"
    estado_http = 503
    mensaje_por_defecto = _lazy(
        "Integración pendiente: falta identificar el equipo aliado y su contrato de API."
    )
