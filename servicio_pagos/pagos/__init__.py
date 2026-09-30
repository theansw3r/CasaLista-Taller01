import logging
import uuid

from flask import Flask, g, request

from pagos.config import Config
from pagos.errores import registrar_manejadores
from pagos.modelos import db
from pagos.reservas import ClienteReservas
from pagos.rutas import bp as rutas_de_pagos


def crear_app(configuracion: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if configuracion:
        app.config.update(configuracion)
    app.json.sort_keys = False

    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    db.init_app(app)
    app.extensions["cliente_reservas"] = ClienteReservas(
        url_base=app.config["URL_RESERVAS"],
        token_servicio=app.config["TOKEN_SERVICIO_PAGOS"],
        timeout=app.config["TIMEOUT_RESERVAS"],
    )

    registrar_manejadores(app)
    app.register_blueprint(rutas_de_pagos)

    # Mismo X-Request-ID que usa Django, para poder seguir una peticion que
    # pasa por Nginx -> Flask -> Django en los logs de los tres.
    @app.before_request
    def identificar_peticion():
        g.id_peticion = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def devolver_identificador(respuesta):
        respuesta.headers["X-Request-ID"] = g.get("id_peticion", "")
        return respuesta

    @app.cli.command("crear-tablas")
    def crear_tablas():
        """Crea la tabla de pagos si todavia no existe."""
        db.create_all()
        print("Tablas del servicio de pagos listas.")

    return app
