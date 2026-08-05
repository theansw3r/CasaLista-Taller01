class ReservaError(Exception):
    # Error controlado del caso de uso Crear Reserva.
    pass


class DatosReservaInvalidos(ReservaError):
    pass


class BloqueNoDisponible(ReservaError):
    pass


class ProfesionalNoValido(ReservaError):
    pass


class ServiciosInvalidos(ReservaError):
    pass
