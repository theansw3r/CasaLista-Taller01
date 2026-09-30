from conftest import TOKEN_CLIENTE, TOKEN_OTRO

from pagos.modelos import Pago, db
from pagos.pasarelas import PasarelaDePago

URL = "/api/v2/pagos/"
CABECERAS = {"Authorization": TOKEN_CLIENTE}


def pagar(cliente, reserva_id=1, medio="TARJETA", cabeceras=CABECERAS):
    return cliente.post(
        URL, json={"reserva_id": reserva_id, "medio": medio}, headers=cabeceras
    )


def pagos_guardados():
    return db.session.execute(db.select(Pago)).scalars().all()


# ------------------------------------------------------------------ POST


def test_201_cobra_y_confirma_la_reserva(cliente, reservas):
    reservas.agregar(1)

    respuesta = pagar(cliente)

    assert respuesta.status_code == 201
    assert respuesta.json["estado"] == "APROBADO"
    assert respuesta.json["estado_reserva"] == "CONFIRMADA"
    assert reservas.confirmadas == [1]


def test_responde_los_mismos_campos_que_la_v1(cliente, reservas):
    reservas.agregar(1, total="85000")

    datos = pagar(cliente).json

    assert list(datos) == [
        "id",
        "reserva_id",
        "estado_reserva",
        "monto",
        "medio",
        "estado",
        "pasarela",
        "referencia_externa",
        "creado_en",
    ]
    assert datos["monto"] == "85000.00"


def test_400_si_el_cuerpo_no_es_json(cliente, reservas):
    respuesta = cliente.post(
        URL, data="reserva=1", headers=CABECERAS, content_type="text/plain"
    )

    assert respuesta.status_code == 400
    assert respuesta.json["error"]["codigo"] == "VAL-000"


def test_400_dice_que_campos_estan_mal(cliente, reservas):
    respuesta = cliente.post(
        URL, json={"reserva_id": 0, "medio": "TRUEQUE"}, headers=CABECERAS
    )

    assert respuesta.status_code == 400
    assert set(respuesta.json["error"]["contexto"]["campos"]) == {"reserva_id", "medio"}


def test_401_sin_token(cliente, reservas):
    respuesta = pagar(cliente, cabeceras={})

    assert respuesta.status_code == 401
    assert respuesta.json["error"]["codigo"] == "HTTP-401"


def test_403_de_django_se_devuelve_igual(cliente, reservas):
    reservas.agregar(1, dueno=TOKEN_OTRO)

    respuesta = pagar(cliente)

    assert respuesta.status_code == 403
    assert respuesta.json["error"]["codigo"] == "VAL-403"


def test_404_si_la_reserva_no_existe(cliente, reservas):
    respuesta = pagar(cliente, reserva_id=999)

    assert respuesta.status_code == 404
    assert respuesta.json["error"]["codigo"] == "RES-04"


def test_409_si_la_reserva_no_esta_pendiente(cliente, reservas):
    reservas.agregar(1, estado="CANCELADA")

    respuesta = pagar(cliente)

    assert respuesta.status_code == 409
    assert respuesta.json["error"]["codigo"] == "PAG-03"
    assert pagos_guardados() == []


def test_un_rechazo_queda_registrado_y_no_deja_reintentar(app, cliente, reservas):
    app.config["PASARELA_PAGO_TYPE"] = "TARJETA"
    reservas.agregar(1, total="500.00")  # la tarjeta pide minimo $1000

    primero = pagar(cliente)
    segundo = pagar(cliente)

    assert primero.status_code == 409
    assert primero.json["error"]["codigo"] == "PAG-04"
    assert segundo.json["error"]["codigo"] == "PAG-02"
    assert pagos_guardados()[0].estado == Pago.RECHAZADO
    assert reservas.reservas[1]["estado"] == "PENDIENTE"


def test_503_si_django_no_responde(cliente, reservas):
    reservas.caido = True

    respuesta = pagar(cliente)

    assert respuesta.status_code == 503
    assert respuesta.json["error"]["codigo"] == "PAG-06"


def test_502_si_se_cobra_pero_no_se_confirma_el_pago_no_se_pierde(cliente, reservas):
    reservas.agregar(1)
    reservas.falla_al_confirmar = True

    respuesta = pagar(cliente)

    assert respuesta.status_code == 502
    assert respuesta.json["error"]["codigo"] == "PAG-07"
    pago = pagos_guardados()[0]
    assert pago.estado == Pago.APROBADO
    assert pago.reserva_confirmada is False


def test_500_en_json_si_la_pasarela_revienta(cliente, reservas, monkeypatch):
    class PasarelaRota(PasarelaDePago):
        nombre = "ROTA"

        def cobrar(self, monto, referencia_interna):
            raise RuntimeError("se cayo la conexion con el banco")

    monkeypatch.setattr(
        "pagos.servicio.pasarela_para", lambda medio, configuracion: PasarelaRota()
    )
    reservas.agregar(1)

    respuesta = pagar(cliente)

    assert respuesta.status_code == 500
    assert respuesta.json["error"]["codigo"] == "HTTP-500"
    assert "banco" not in respuesta.get_data(as_text=True)
    assert pagos_guardados() == []  # se libero para poder reintentar


# ------------------------------------------------------------------ GET


def test_200_consulta_del_pago_propio(cliente, reservas):
    reservas.agregar(1)
    pago_id = pagar(cliente).json["id"]

    respuesta = cliente.get(f"{URL}{pago_id}/", headers=CABECERAS)

    assert respuesta.status_code == 200
    assert respuesta.json["id"] == pago_id
    assert respuesta.json["estado_reserva"] == "CONFIRMADA"


def test_403_al_consultar_el_pago_de_otro(cliente, reservas):
    reservas.agregar(1)
    pago_id = pagar(cliente).json["id"]

    respuesta = cliente.get(f"{URL}{pago_id}/", headers={"Authorization": TOKEN_OTRO})

    assert respuesta.status_code == 403


def test_404_si_el_pago_no_existe(cliente, reservas):
    respuesta = cliente.get(f"{URL}999/", headers=CABECERAS)

    assert respuesta.status_code == 404
    assert respuesta.json["error"]["codigo"] == "PAG-01"


# ------------------------------------------------------------------ varios


def test_rutas_desconocidas_tambien_responden_json(cliente):
    respuesta = cliente.get("/api/v2/pagos/no-existe/")

    assert respuesta.status_code == 404
    assert respuesta.json["error"]["codigo"] == "HTTP-404"


def test_405_en_json(cliente):
    respuesta = cliente.delete(URL)

    assert respuesta.status_code == 405
    assert respuesta.json["error"]["codigo"] == "HTTP-405"


def test_salud(cliente):
    respuesta = cliente.get(f"{URL}salud/")

    assert respuesta.status_code == 200
    assert respuesta.json["base_de_datos"] == "ok"


def test_devuelve_el_mismo_id_de_peticion(cliente):
    respuesta = cliente.get(f"{URL}salud/", headers={"X-Request-ID": "abc123"})

    assert respuesta.headers["X-Request-ID"] == "abc123"
