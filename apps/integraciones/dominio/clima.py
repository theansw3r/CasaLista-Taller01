from dataclasses import dataclass


@dataclass(frozen=True)
class CondicionesClima:
    """Lo que CasaLista necesita saber del clima, sin importar quien lo da.

    El resto del sistema solo conoce este objeto. Si manana se cambia de
    proveedor, se escribe otro adaptador que devuelva lo mismo.
    """

    ciudad: str
    temperatura_c: float
    precipitacion_mm: float
    observado_en: str
    zona_horaria: str
    fuente: str
    atribucion: str
