"""
Capa de aplicacion del modulo Catalogo.

Aunque sean casos de uso de solo lectura, viven igual en un servicio. La razon
es RN-07: "un profesional solo aparece en resultados si esta verificado y su
cobertura incluye la direccion del cliente". Eso es una regla de negocio, y si
se escribiera como `.filter(...)` dentro de la vista quedaria logica de
negocio en la capa de presentacion.
"""

from apps.catalogo.dominio.excepciones import ProfesionalNoEncontrado
from apps.catalogo.models import Servicio
from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.models import Profesional


class CatalogoService:
    """Caso de uso: un cliente explora la oferta antes de reservar."""

    def buscar_profesionales(self, zona: str = "", texto: str = ""):
        """Profesionales que RN-07 permite mostrar, opcionalmente filtrados.

        El filtro por zona se hace en dos pasos a proposito:

        1. la base de datos descarta lo obvio (`icontains`), que es barato;
        2. la politica de dominio decide de verdad, porque comparar zonas
           ignorando mayusculas y espacios es una regla, no una consulta.

        Si algun dia las zonas se normalizan en su propia tabla, cambia el
        paso 1 y el paso 2 se queda igual.
        """
        consulta = Profesional.objects.filter(verificado=True)
        if texto:
            consulta = consulta.filter(nombre__icontains=texto)
        if zona:
            consulta = consulta.filter(zonas_cobertura__icontains=zona.strip())
            return [
                profesional
                for profesional in consulta
                if PoliticaDeCobertura.cubre_zona(profesional, zona)
            ]
        return list(consulta)

    def servicios_de(self, profesional_id: int, solo_activos: bool = True):
        """Catalogo publicado por un profesional. 404 si el profesional no existe."""
        profesional = self._obtener_profesional(profesional_id)
        consulta = Servicio.objects.filter(profesional=profesional).select_related(
            "profesional"
        )
        if solo_activos:
            consulta = consulta.filter(activo=True)
        return list(consulta)

    @staticmethod
    def _obtener_profesional(profesional_id: int) -> Profesional:
        """Traduce el "no existe" del ORM al lenguaje del dominio.

        Este metodo es la frontera: de aqui hacia arriba nadie vuelve a ver un
        `DoesNotExist` de Django, solo excepciones del negocio.
        """
        try:
            return Profesional.objects.get(pk=profesional_id, verificado=True)
        except Profesional.DoesNotExist:
            raise ProfesionalNoEncontrado(
                f"No existe un profesional verificado con id {profesional_id}.",
                profesional_id=profesional_id,
            ) from None
