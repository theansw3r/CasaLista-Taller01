import math

import requests
from django.utils.translation import gettext as _

from apps.comun.dominio.excepciones import ErrorDeDominio


class ProveedorNoDisponible(ErrorDeDominio):
    codigo = "INT-503"
    estado_http = 503


class OpenMeteoAdapter:
    """Traduce el contrato externo a condiciones para planear visitas en Medellín.

    La URL es fija: no se aceptan URLs ni coordenadas privadas desde el cliente.
    """
    URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, sesion=None):
        self.sesion = sesion or requests.Session()

    def condiciones(self):
        try:
            respuesta = self.sesion.get(
                self.URL,
                params={"latitude": 6.2442, "longitude": -75.5812,
                        "current": "temperature_2m,precipitation",
                        "timezone": "America/Bogota"},
                timeout=(2, 4), allow_redirects=False,
            )
            if respuesta.status_code != 200:
                raise ValueError("status")
            dato = respuesta.json()
            actual = dato["current"]
            temperatura = actual["temperature_2m"]
            lluvia = actual["precipitation"]
            for valor in (temperatura, lluvia):
                if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                    raise ValueError("numeric")
            if not isinstance(actual["time"], str) or lluvia < 0:
                raise ValueError("schema")
            unidades = dato["current_units"]
            if unidades["temperature_2m"] != "°C" or unidades["precipitation"] != "mm":
                raise ValueError("units")
            return {"ciudad": "Medellín", "temperatura_c": temperatura,
                    "precipitacion_mm": lluvia, "observado_en": actual["time"],
                    "zona_horaria": "America/Bogota", "fuente": "Open-Meteo",
                    "atribucion": "https://open-meteo.com/"}
        except (requests.RequestException, ValueError, KeyError, TypeError):
            raise ProveedorNoDisponible(_("El clima no está disponible. Puedes continuar tu reserva.")) from None
