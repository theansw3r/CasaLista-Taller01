from django.utils.translation import gettext_lazy as _lazy

from apps.comun.dominio.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada


class PagoNoEncontrado(RecursoNoEncontrado):
    codigo = "PAG-01"
    mensaje_por_defecto = _lazy("El pago solicitado no existe.")


class ReservaYaPagada(ReglaDeNegocioViolada):

    codigo = "PAG-02"
    mensaje_por_defecto = _lazy("Esta reserva ya tiene un pago registrado.")


class ReservaNoCobrable(ReglaDeNegocioViolada):

    codigo = "PAG-03"
    mensaje_por_defecto = _lazy("La reserva no está en un estado que admita pago.")


class PagoRechazado(ReglaDeNegocioViolada):

    codigo = "PAG-04"
    mensaje_por_defecto = _lazy("La pasarela rechazó el pago.")


class PasarelaNoDisponible(ReglaDeNegocioViolada):

    codigo = "PAG-05"
    estado_http = 502
    mensaje_por_defecto = _lazy("La pasarela de pagos no está respondiendo.")
