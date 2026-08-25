from django.db import IntegrityError

from apps.catalogo.dominio.estandares import EstandaresDeCasaLista
from apps.catalogo.dominio.excepciones import (
    ProfesionalNoEncontrado,
    ServicioDuplicado,
    ServicioNoEncontrado,
)
from apps.catalogo.dto import PublicarServicioCommand
from apps.catalogo.models import Servicio
from apps.cuentas.dominio.cobertura import PoliticaDeCobertura
from apps.cuentas.models import Profesional
from apps.cuentas.services import ConsultaPerfilService


class CatalogoService:

    def buscar_profesionales(self, zona: str = "", texto: str = "", categoria: str = ""):
        consulta = Profesional.objects.filter(verificado=True)
        if texto:
            consulta = consulta.filter(nombre__icontains=texto)
        if categoria:
            # Solo tiene sentido mostrar a quien publico algo de ese oficio y
            # lo tiene activo: si no, el cliente entra al perfil y no hay nada.
            consulta = consulta.filter(
                servicios__categoria=categoria, servicios__activo=True
            ).distinct()
        if zona:
            consulta = consulta.filter(zonas_cobertura__icontains=zona.strip())
            return [
                profesional
                for profesional in consulta
                if PoliticaDeCobertura.cubre_zona(profesional, zona)
            ]
        return list(consulta)

    def servicios_de(self, profesional_id: int, solo_activos: bool = True):
        profesional = self._obtener_profesional(profesional_id)
        consulta = Servicio.objects.filter(profesional=profesional).select_related(
            "profesional"
        )
        if solo_activos:
            consulta = consulta.filter(activo=True)
        return list(consulta)

    @staticmethod
    def _obtener_profesional(profesional_id: int) -> Profesional:
        try:
            return Profesional.objects.get(pk=profesional_id, verificado=True)
        except Profesional.DoesNotExist:
            raise ProfesionalNoEncontrado(
                f"No existe un profesional verificado con id {profesional_id}.",
                profesional_id=profesional_id,
            ) from None


class PublicacionServicioService:
    """Caso de uso: un profesional publica y administra su catalogo."""

    def publicar(self, comando: PublicarServicioCommand) -> Servicio:
        profesional = ConsultaPerfilService.profesional_de(comando.usuario_id)

        # El nicho de CasaLista no admite cualquier servicio: la categoria la
        # restringe el modelo, y estas dos reglas las exige el dominio.
        EstandaresDeCasaLista.exigir_duracion_de_visita(comando.duracion_minutos)
        EstandaresDeCasaLista.exigir_descripcion_util(comando.descripcion)

        try:
            return Servicio.objects.create(
                profesional=profesional,
                categoria=comando.categoria,
                nombre=comando.nombre.strip(),
                descripcion=comando.descripcion.strip(),
                precio_base=comando.precio_base,
                duracion_minutos=comando.duracion_minutos,
                requiere_visita_previa=comando.requiere_visita_previa,
            )
        except IntegrityError:
            raise ServicioDuplicado(
                f"Ya tienes un servicio llamado '{comando.nombre}'.",
                nombre=comando.nombre,
            ) from None

    def mis_servicios(self, usuario_id: int):
        """Incluye los inactivos: el profesional administra todo su catalogo."""
        profesional = ConsultaPerfilService.profesional_de(usuario_id)
        return list(
            Servicio.objects.filter(profesional=profesional).select_related(
                "profesional"
            )
        )

    def cambiar_disponibilidad(self, usuario_id: int, servicio_id: int, activo: bool):
        profesional = ConsultaPerfilService.profesional_de(usuario_id)
        try:
            servicio = Servicio.objects.get(pk=servicio_id, profesional=profesional)
        except Servicio.DoesNotExist:
            raise ServicioNoEncontrado(
                f"No tienes un servicio con id {servicio_id}.", servicio_id=servicio_id
            ) from None
        servicio.activo = activo
        servicio.save(update_fields=["activo"])
        return servicio
