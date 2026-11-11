from django.utils.translation import gettext as _

from apps.cuentas.dominio.excepciones import ProfesionalNoHabilitado


class PoliticaDeCobertura:

    @staticmethod
    def zonas_de(profesional) -> list[str]:
        crudo = profesional.zonas_cobertura or ""
        return [zona.strip() for zona in crudo.split(",") if zona.strip()]

    @classmethod
    def cubre_zona(cls, profesional, zona: str) -> bool:
        objetivo = (zona or "").strip().casefold()
        if not objetivo:
            return False
        return objetivo in {z.casefold() for z in cls.zonas_de(profesional)}

    @classmethod
    def esta_habilitado(cls, profesional, zona: str) -> bool:
        return profesional.verificado and cls.cubre_zona(profesional, zona)

    @classmethod
    def exigir_habilitado(cls, profesional, zona: str) -> None:
        if not profesional.verificado:
            raise ProfesionalNoHabilitado(
                _("El profesional %(profesional)s todavía no está verificado.") % {"profesional": profesional.nombre},
                profesional_id=profesional.pk,
            )
        if not cls.cubre_zona(profesional, zona):
            raise ProfesionalNoHabilitado(
                _("El profesional %(profesional)s no cubre la zona '%(zona)s'.") % {"profesional": profesional.nombre, "zona": zona},
                zona_solicitada=zona,
                zonas_cubiertas=cls.zonas_de(profesional),
            )
