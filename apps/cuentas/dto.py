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
    descripcion: str = ""
    zonas_cobertura: tuple[str, ...] = ()
