import pytest

from pagos import crear_app
from pagos.errores import ErrorDeReservas, ReservasNoDisponible
from pagos.modelos import db

TOKEN_CLIENTE = "Bearer token-de-laura"
TOKEN_OTRO = "Bearer token-de-otro"


class ReservasFalsas:
    """Hace de Django en las pruebas, para no tener que levantar el monolito."""

    def __init__(self) -> None:
        self.reservas = {}
        self.caido = False
        self.falla_al_confirmar = False
        self.confirmadas = []

    def agregar(self, reserva_id, total="50000.00", estado="PENDIENTE", dueno=TOKEN_CLIENTE):
        self.reservas[reserva_id] = {
            "id": reserva_id,
            "estado": estado,
            "total": total,
            "dueno": dueno,
        }

    def obtener(self, reserva_id, autorizacion, id_peticion=""):
        if self.caido:
            raise ReservasNoDisponible()
        reserva = self.reservas.get(reserva_id)
        if reserva is None:
            raise ErrorDeReservas(
                404, {"error": {"codigo": "RES-04", "mensaje": "No existe la reserva."}}
            )
        if reserva["dueno"] != autorizacion:
            raise ErrorDeReservas(
                403,
                {"error": {"codigo": "VAL-403", "mensaje": "La reserva pertenece a otro cliente."}},
            )
        return dict(reserva)

    def confirmar(self, reserva_id, id_peticion=""):
        if self.falla_al_confirmar:
            raise ReservasNoDisponible()
        self.reservas[reserva_id]["estado"] = "CONFIRMADA"
        self.confirmadas.append(reserva_id)
        return dict(self.reservas[reserva_id])


@pytest.fixture
def app():
    app = crear_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "PASARELA_PAGO_TYPE": "SIMULADA",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def reservas(app):
    falsas = ReservasFalsas()
    app.extensions["cliente_reservas"] = falsas
    return falsas


@pytest.fixture
def cliente(app):
    return app.test_client()
