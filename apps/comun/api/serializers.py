"""
Serializers transversales.

`ErrorSerializer` no se usa para responder (el manejador de errores arma el
diccionario a mano), pero si para DOCUMENTAR: gracias a el, el esquema OpenAPI
publica la forma exacta que tiene un error de la API. Eso es lo que le permite
al API Gateway y a quien consuma la API programar contra un contrato y no
contra ejemplos.
"""

from rest_framework import serializers


class SaludSerializer(serializers.Serializer):
    servicio = serializers.CharField()
    version = serializers.CharField()
    base_de_datos = serializers.CharField()
    id_peticion = serializers.CharField(allow_null=True)


class DetalleErrorSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Regla violada. Ej: RN-01, VAL-404.")
    mensaje = serializers.CharField()
    contexto = serializers.DictField(required=False)


class ErrorSerializer(serializers.Serializer):
    """Forma unica de todos los errores de la API."""

    error = DetalleErrorSerializer()
