"""
Creacion de reservas.

ADVERTENCIA: esta implementacion mezcla parsing HTTP, reglas de negocio,
acceso a datos y envio de correo en una sola funcion. Es el punto de partida
del Taller 01 y sera refactorizada.
"""

import json
from decimal import Decimal

from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import BloqueDisponibilidad, DetalleReserva, Reserva, Servicio


@require_POST
def crear_reserva(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)

    cliente = getattr(request.user, "cliente", None)
    if cliente is None:
        return JsonResponse({"error": "El usuario no es un cliente"}, status=403)

    # ---- parsing manual del request -------------------------------------
    try:
        payload = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"error": "JSON invalido"}, status=400)

    bloque_id = payload.get("bloque_id")
    direccion = payload.get("direccion")
    zona = payload.get("zona")
    lineas = payload.get("servicios")
    if not bloque_id or not direccion or not zona or not lineas:
        return JsonResponse({"error": "Faltan datos obligatorios"}, status=400)

    # ---- acceso a datos directamente en la vista ------------------------
    try:
        bloque = BloqueDisponibilidad.objects.get(pk=bloque_id)
    except BloqueDisponibilidad.DoesNotExist:
        return JsonResponse({"error": "El bloque no existe"}, status=404)

    servicios = []
    for linea in lineas:
        try:
            servicio = Servicio.objects.get(pk=linea.get("servicio_id"))
        except Servicio.DoesNotExist:
            return JsonResponse({"error": "Servicio inexistente"}, status=404)
        cantidad = int(linea.get("cantidad", 1))
        if cantidad <= 0:
            return JsonResponse({"error": "Cantidad invalida"}, status=400)
        if not servicio.activo:
            return JsonResponse({"error": "Servicio inactivo"}, status=400)
        servicios.append((servicio, cantidad))

    # ---- reglas de negocio enredadas con la vista -----------------------
    profesional = servicios[0][0].profesional
    for servicio, _cantidad in servicios:
        if servicio.profesional_id != profesional.id:
            return JsonResponse(
                {"error": "Los servicios deben ser del mismo profesional"}, status=400
            )

    if not profesional.verificado:
        return JsonResponse({"error": "El profesional no esta verificado"}, status=400)

    if zona.strip().lower() not in [
        z.strip().lower() for z in profesional.zonas_cobertura.split(",")
    ]:
        return JsonResponse({"error": "El profesional no cubre la zona"}, status=400)

    if bloque.profesional_id != profesional.id:
        return JsonResponse({"error": "El bloque es de otro profesional"}, status=400)

    if bloque.estado != "LIBRE":
        return JsonResponse({"error": "El bloque ya esta ocupado"}, status=409)

    if Reserva.objects.filter(
        Q(bloque=bloque) & Q(estado__in=["PENDIENTE", "CONFIRMADA"])
    ).exists():
        return JsonResponse({"error": "El bloque ya tiene una reserva"}, status=409)

    duracion_pedida = sum(s.duracion_minutos * c for s, c in servicios)
    duracion_bloque = int((bloque.fin - bloque.inicio).total_seconds() // 60)
    if duracion_pedida > duracion_bloque:
        return JsonResponse({"error": "Los servicios no caben en el bloque"}, status=400)

    # ---- calculo de tarifa embebido en la vista -------------------------
    total = Decimal("0.00")
    for servicio, cantidad in servicios:
        total += servicio.precio_base * cantidad
    if bloque.inicio.hour >= 19 or bloque.inicio.hour < 7:
        total = total * Decimal("1.20")
    if bloque.inicio.weekday() >= 5:
        total = total * Decimal("1.15")

    # ---- persistencia sin transaccion -----------------------------------
    reserva = Reserva.objects.create(
        cliente=cliente,
        profesional=profesional,
        bloque=bloque,
        direccion=direccion,
        zona=zona,
        estado="PENDIENTE",
        total=total,
    )
    for servicio, cantidad in servicios:
        DetalleReserva.objects.create(
            reserva=reserva,
            servicio=servicio,
            cantidad=cantidad,
            precio_unitario=servicio.precio_base,
            duracion_unitaria_minutos=servicio.duracion_minutos,
        )
    bloque.estado = "OCUPADO"
    bloque.save()

    # ---- envio de correo acoplado a la vista ----------------------------
    send_mail(
        subject=f"Reserva #{reserva.id} creada",
        message=f"Tu reserva por {reserva.total} quedo en estado PENDIENTE.",
        from_email="no-reply@casalista.co",
        recipient_list=[request.user.email],
        fail_silently=True,
    )

    return JsonResponse(
        {"id": reserva.id, "estado": reserva.estado, "total": str(reserva.total)},
        status=201,
    )
