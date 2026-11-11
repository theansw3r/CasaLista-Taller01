from rest_framework import serializers


class CondicionesClimaSerializer(serializers.Serializer):
    ciudad = serializers.CharField()
    temperatura_c = serializers.FloatField()
    precipitacion_mm = serializers.FloatField()
    observado_en = serializers.CharField()
    zona_horaria = serializers.CharField()
    fuente = serializers.CharField()
    atribucion = serializers.URLField()
