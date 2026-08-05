"""Traduccion de entidades de dominio a la representacion que viaja por HTTP."""


def serializar_reserva(reserva) -> dict:
    return {
        "id": reserva.pk,
        "estado": reserva.estado,
        "total": str(reserva.total),
        "tarifa_aplicada": reserva.tarifa_aplicada,
        "profesional": reserva.profesional.nombre,
        "inicio": reserva.bloque.inicio.isoformat(),
        "fin": reserva.bloque.fin.isoformat(),
        "direccion": reserva.direccion,
        "detalles": [
            {
                "servicio": detalle.servicio.nombre,
                "cantidad": detalle.cantidad,
                "precio_unitario": str(detalle.precio_unitario),
                "subtotal": str(detalle.calcular_subtotal()),
            }
            for detalle in reserva.detalles.select_related("servicio")
        ],
    }
