from django.db import connection


class SaludService:
    """Caso de uso de operacion: informar si la instancia puede atender.

    Vive en un servicio y no en la vista por la misma razon que el resto:
    `views.py` solo traduce HTTP. Consultar la base de datos y decidir si la
    instancia esta sana es trabajo de la capa de aplicacion.
    """

    VERSION = "1.0.0"
    NOMBRE = "casalista-api"

    def estado(self) -> tuple[dict, bool]:
        """Devuelve el reporte y si la instancia esta sana."""
        viva = self._base_de_datos_responde()
        reporte = {
            "servicio": self.NOMBRE,
            "version": self.VERSION,
            "base_de_datos": "ok" if viva else "sin-conexion",
        }
        return reporte, viva

    @staticmethod
    def _base_de_datos_responde() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False


class IndiceService:
    """Lista los puntos de entrada publicos de la API."""

    def describir(self) -> dict:
        return {
            "api": "CasaLista",
            "version": SaludService.VERSION,
            "endpoints": {
                "cuentas": "/api/v1/cuentas/",
                "catalogo": "/api/v1/catalogo/profesionales/",
                "disponibilidad": "/api/v1/reservas/disponibilidad/",
                "reservas": "/api/v1/reservas/",
                "pagos": "/api/v1/pagos/",
                "pagos_v2": "/api/v2/pagos/",
                "salud": "/api/v1/salud/",
            },
        }
