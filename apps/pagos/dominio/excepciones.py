"""Errores de negocio del modulo Pagos."""

from apps.comun.dominio.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada


class PagoNoEncontrado(RecursoNoEncontrado):
    codigo = "PAG-01"
    mensaje_por_defecto = "El pago solicitado no existe."


class ReservaYaPagada(ReglaDeNegocioViolada):
    """Una reserva no se cobra dos veces (cardinalidad 0..1 del diagrama)."""

    codigo = "PAG-02"
    mensaje_por_defecto = "Esta reserva ya tiene un pago registrado."


class ReservaNoCobrable(ReglaDeNegocioViolada):
    """Solo se cobra una reserva que sigue esperando pago.

    Cobrar una reserva cancelada o ya confirmada seria cobrar dos veces o
    cobrar algo que no se va a prestar.
    """

    codigo = "PAG-03"
    mensaje_por_defecto = "La reserva no esta en un estado que admita pago."


class PagoRechazado(ReglaDeNegocioViolada):
    """La pasarela no aprobo la transaccion.

    Es un 409 y no un 502: la pasarela respondio correctamente, lo que pasa es
    que la respuesta fue "no". Un 502 diria que el sistema fallo, y no fallo.
    """

    codigo = "PAG-04"
    mensaje_por_defecto = "La pasarela rechazo el pago."


class PasarelaNoDisponible(ReglaDeNegocioViolada):
    """La pasarela no contesto. Esto si es un fallo de infraestructura."""

    codigo = "PAG-05"
    estado_http = 502
    mensaje_por_defecto = "La pasarela de pagos no esta respondiendo."
