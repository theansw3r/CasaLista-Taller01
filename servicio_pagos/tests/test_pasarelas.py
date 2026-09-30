from decimal import Decimal

from pagos.pasarelas import PasarelaPSE, PasarelaSimulada, PasarelaTarjeta, pasarela_para


def test_con_simulada_se_ignora_el_medio():
    assert isinstance(pasarela_para("TARJETA", "SIMULADA"), PasarelaSimulada)
    assert isinstance(pasarela_para("PSE", "simulada"), PasarelaSimulada)


def test_en_modo_real_se_usa_la_del_medio():
    assert isinstance(pasarela_para("TARJETA", "TARJETA"), PasarelaTarjeta)
    assert isinstance(pasarela_para("PSE", "TARJETA"), PasarelaPSE)


def test_la_tarjeta_rechaza_montos_menores_al_minimo():
    resultado = PasarelaTarjeta().cobrar(Decimal("999.99"), "reserva-1")

    assert not resultado.aprobado
    assert "minimo" in resultado.motivo
