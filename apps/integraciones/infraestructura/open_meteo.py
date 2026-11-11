import math

import requests

from apps.integraciones.dominio.clima import CondicionesClima
from apps.integraciones.dominio.excepciones import ProveedorNoDisponible
from apps.integraciones.dominio.puertos import ProveedorClima


class _RespuestaInvalida(Exception):
    """Open-Meteo respondio, pero no con el contrato que esperamos."""


class OpenMeteoAdapter(ProveedorClima):
    """Adapter: traduce el API de Open-Meteo a CondicionesClima.

    La URL y las coordenadas son fijas. El cliente de CasaLista nunca manda
    una URL ni una ubicacion, asi que no se puede usar para pedirle cosas a
    otros servidores ni filtra direcciones de clientes.
    """

    nombre = "OPEN_METEO"

    URL = "https://api.open-meteo.com/v1/forecast"
    CIUDAD = "Medellín"
    LATITUD = 6.2442
    LONGITUD = -75.5812
    ZONA_HORARIA = "America/Bogota"
    ATRIBUCION = "https://open-meteo.com/"
    TIEMPO_CONEXION_S = 2
    TIEMPO_LECTURA_S = 4

    def __init__(self, sesion: requests.Session | None = None) -> None:
        self.sesion = sesion or requests.Session()

    def condiciones(self) -> CondicionesClima:
        try:
            return self._traducir(self._consultar())
        except (requests.RequestException, _RespuestaInvalida, KeyError, TypeError):
            raise ProveedorNoDisponible() from None

    def _consultar(self) -> dict:
        respuesta = self.sesion.get(
            self.URL,
            params={
                "latitude": self.LATITUD,
                "longitude": self.LONGITUD,
                "current": "temperature_2m,precipitation",
                "timezone": self.ZONA_HORARIA,
            },
            timeout=(self.TIEMPO_CONEXION_S, self.TIEMPO_LECTURA_S),
            allow_redirects=False,
        )
        if respuesta.status_code != 200:
            raise _RespuestaInvalida(f"HTTP {respuesta.status_code}")
        try:
            return respuesta.json()
        except ValueError as error:
            raise _RespuestaInvalida("el cuerpo no es JSON") from error

    def _traducir(self, dato: dict) -> CondicionesClima:
        actual = dato["current"]
        unidades = dato["current_units"]
        temperatura = self._numero(actual["temperature_2m"])
        lluvia = self._numero(actual["precipitation"])

        if lluvia < 0 or not isinstance(actual["time"], str):
            raise _RespuestaInvalida("valores fuera de rango")
        if unidades["temperature_2m"] != "°C" or unidades["precipitation"] != "mm":
            raise _RespuestaInvalida("unidades inesperadas")

        return CondicionesClima(
            ciudad=self.CIUDAD,
            temperatura_c=temperatura,
            precipitacion_mm=lluvia,
            observado_en=actual["time"],
            zona_horaria=self.ZONA_HORARIA,
            fuente="Open-Meteo",
            atribucion=self.ATRIBUCION,
        )

    @staticmethod
    def _numero(valor) -> float:
        # bool es subclase de int en Python: True pasaria como 1 sin esto.
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            raise _RespuestaInvalida("no es un numero")
        if not math.isfinite(valor):
            raise _RespuestaInvalida("numero no finito")
        return valor
