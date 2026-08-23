"""
Puerto de la pasarela de pagos.

Este es el ejemplo mas claro de por que existe la carpeta `dominio/`: cobrar
con tarjeta y cobrar con PSE son dos integraciones completamente distintas
(protocolos, credenciales, tiempos de respuesta), pero para el negocio son la
misma frase: "cobrame este monto y dime si paso".

El dominio declara esa frase aqui. Como se cumple es problema de
`infraestructura/`, y cual se usa lo decide `PasarelaPagoFactory`.

`ResultadoPago` es un objeto de valor y no un diccionario a proposito: un
diccionario obliga a cada llamador a recordar las claves y no falla hasta
tiempo de ejecucion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResultadoPago:
    """Lo que responde una pasarela, en el vocabulario del negocio."""

    aprobado: bool
    referencia: str = ""
    motivo: str = ""


class PasarelaDePago(ABC):
    """Puerto de salida hacia el proveedor que mueve el dinero."""

    nombre = "ABSTRACTA"

    @abstractmethod
    def cobrar(self, monto: Decimal, referencia_interna: str) -> ResultadoPago:
        """Intenta cobrar `monto`. Devuelve el resultado, no lanza por rechazo.

        Un rechazo es una respuesta valida del negocio, asi que viaja como
        dato. Solo se lanza excepcion si la pasarela no responde.
        """
