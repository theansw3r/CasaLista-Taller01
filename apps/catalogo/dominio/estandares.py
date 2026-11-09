from django.utils.translation import gettext as _, gettext_lazy as _lazy
from apps.catalogo.dominio.excepciones import ServicioFueraDeEstandar


class EstandaresDeCasaLista:
    """Que se puede publicar en el catalogo y que no.

    El nicho no es "servicios en general": la seccion 1.1 del Business Case lo
    limita a oficios tecnicos de visita corta y agendable, con visitas de entre
    una y cuatro horas. Esa delimitacion es lo que hace posible modelar una
    agenda real, asi que el catalogo tiene que hacerla cumplir.
    """

    DURACION_MINIMA_MINUTOS = 60
    DURACION_MAXIMA_MINUTOS = 240
    LARGO_MINIMO_DESCRIPCION = 20

    @classmethod
    def exigir_duracion_de_visita(cls, minutos: int) -> None:
        if minutos < cls.DURACION_MINIMA_MINUTOS:
            raise ServicioFueraDeEstandar(
                _("Una visita no puede durar menos de %(v0)s minutos.") % {'v0': cls.DURACION_MINIMA_MINUTOS},
                minutos_recibidos=minutos,
                minimo=cls.DURACION_MINIMA_MINUTOS,
            )
        if minutos > cls.DURACION_MAXIMA_MINUTOS:
            raise ServicioFueraDeEstandar(
                _("CasaLista solo agenda visitas de hasta %(v0)s minutos (cuatro horas). Un trabajo mas largo se divide en varias visitas.") % {'v0': cls.DURACION_MAXIMA_MINUTOS},
                minutos_recibidos=minutos,
                maximo=cls.DURACION_MAXIMA_MINUTOS,
            )

    @classmethod
    def exigir_descripcion_util(cls, descripcion: str) -> None:
        """El cliente contrata sin ver al profesional: necesita saber que compra."""
        limpia = (descripcion or "").strip()
        if len(limpia) < cls.LARGO_MINIMO_DESCRIPCION:
            raise ServicioFueraDeEstandar(
                _("Describe el servicio con al menos %(v0)s caracteres: el cliente decide con esa informacion.") % {'v0': cls.LARGO_MINIMO_DESCRIPCION},
                largo_recibido=len(limpia),
            )
