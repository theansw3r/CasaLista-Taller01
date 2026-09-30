import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///pagos.db")

    # El monolito: de ahi se leen las reservas y ahi se confirman.
    URL_RESERVAS = os.getenv("URL_RESERVAS", "http://localhost:8000")
    TIMEOUT_RESERVAS = float(os.getenv("TIMEOUT_RESERVAS", "5"))

    # Lo tienen que conocer los dos servicios. Django lo pide para dejar que
    # pagos le confirme una reserva.
    TOKEN_SERVICIO_PAGOS = os.getenv("TOKEN_SERVICIO_PAGOS", "")

    # Mismos valores que en Django: SIMULADA / TARJETA / PSE
    PASARELA_PAGO_TYPE = os.getenv("PASARELA_PAGO_TYPE", "SIMULADA")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
