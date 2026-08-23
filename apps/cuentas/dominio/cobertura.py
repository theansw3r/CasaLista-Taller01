"""
Regla RN-07: habilitacion de un profesional.

Este archivo existe porque `cubreZona()` aparece en el diagrama como metodo de
Profesional, pero ponerlo dentro del modelo lo convertiria en un "fat model":
seria logica de negocio en la capa de persistencia. La regla se saca aqui, a
una clase sin estado que recibe la entidad y responde.

Ventaja practica: esta clase se puede probar con un objeto cualquiera que
tenga `verificado` y `zonas_cobertura`, sin base de datos.
"""

from apps.cuentas.dominio.excepciones import ProfesionalNoHabilitado


class PoliticaDeCobertura:
    """Decide si un profesional puede atender en una zona (RN-07)."""

    @staticmethod
    def zonas_de(profesional) -> list[str]:
        """Zonas declaradas por el profesional, ya limpias de espacios."""
        crudo = profesional.zonas_cobertura or ""
        return [zona.strip() for zona in crudo.split(",") if zona.strip()]

    @classmethod
    def cubre_zona(cls, profesional, zona: str) -> bool:
        """True si la cobertura del profesional incluye la zona pedida.

        La comparacion ignora mayusculas y espacios porque la zona la escribe
        el cliente a mano y "laureles" y "Laureles" son la misma.
        """
        objetivo = (zona or "").strip().casefold()
        if not objetivo:
            return False
        return objetivo in {z.casefold() for z in cls.zonas_de(profesional)}

    @classmethod
    def esta_habilitado(cls, profesional, zona: str) -> bool:
        return profesional.verificado and cls.cubre_zona(profesional, zona)

    @classmethod
    def exigir_habilitado(cls, profesional, zona: str) -> None:
        """Version que lanza la excepcion. La usa el Builder de reservas.

        Se separa de `esta_habilitado` a proposito: el catalogo necesita
        filtrar (pregunta), el Builder necesita bloquear (exigencia). Mismo
        criterio, dos formas de consumirlo.
        """
        if not profesional.verificado:
            raise ProfesionalNoHabilitado(
                f"El profesional {profesional.nombre} todavia no esta verificado.",
                profesional_id=profesional.pk,
            )
        if not cls.cubre_zona(profesional, zona):
            raise ProfesionalNoHabilitado(
                f"El profesional {profesional.nombre} no cubre la zona '{zona}'.",
                zona_solicitada=zona,
                zonas_cubiertas=cls.zonas_de(profesional),
            )
