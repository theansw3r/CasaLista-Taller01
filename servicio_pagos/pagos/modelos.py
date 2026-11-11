from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def ahora() -> datetime:
    return datetime.now(UTC)


class Pago(db.Model):
    __tablename__ = "pagos"

    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"

    id = db.Column(db.Integer, primary_key=True)
    # En Django esto era un OneToOneField a Reserva. La reserva ahora vive en
    # otra base de datos, asi que aca solo queda el numero. El unique es lo
    # que evita cobrar dos veces la misma reserva.
    reserva_id = db.Column(db.Integer, nullable=False, unique=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    medio = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default=PENDIENTE)
    pasarela = db.Column(db.String(20), nullable=False)
    referencia_externa = db.Column(db.String(64), nullable=False, default="")
    motivo_rechazo = db.Column(db.String(200), nullable=False, default="")
    # False si se cobro pero Django no alcanzo a confirmar la reserva.
    reserva_confirmada = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=ahora)
    actualizado_en = db.Column(
        db.DateTime(timezone=True), nullable=False, default=ahora, onupdate=ahora
    )

    def __repr__(self) -> str:
        return f"<Pago {self.id} reserva={self.reserva_id} {self.estado}>"
