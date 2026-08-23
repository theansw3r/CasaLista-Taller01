"""
Comandos del modulo Cuentas.

Un comando es lo que la capa de API le entrega al servicio. Es un dataclass
inmutable, sin dependencias de Django: el servicio nunca recibe un `request`
ni un `serializer`, asi que el mismo caso de uso sirve para la API REST, para
un comando de management o para una cola de tareas.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrarClienteCommand:
    correo: str
    contrasena: str
    nombre: str
    telefono: str = ""


@dataclass(frozen=True)
class RegistrarProfesionalCommand:
    correo: str
    contrasena: str
    nombre: str
    documento: str
    zonas_cobertura: tuple[str, ...] = ()
