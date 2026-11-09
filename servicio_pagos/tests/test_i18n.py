def test_error_autenticacion_se_traduce_por_peticion(cliente):
    en=cliente.post('/api/v2/pagos/', json={}, headers={'Accept-Language':'en'})
    es=cliente.post('/api/v2/pagos/', json={}, headers={'Accept-Language':'es'})
    assert en.status_code == es.status_code == 401
    assert en.json['error']['mensaje'] == 'Authentication credentials were not provided.'
    assert es.json['error']['mensaje'] == 'Las credenciales de autenticacion no se proveyeron.'


def test_campos_invalidos_se_traducen(cliente):
    respuesta=cliente.post('/api/v2/pagos/',json={'reserva_id':False},headers={'Authorization':'Bearer x','Accept-Language':'en'})
    assert respuesta.status_code==400
    assert 'integer' in respuesta.json['error']['contexto']['campos']['reserva_id'][0]


def test_estado_en_error_de_pago_se_traduce(cliente,reservas):
    reservas.agregar(44,estado='CONFIRMADA')
    respuesta=cliente.post('/api/v2/pagos/',json={'reserva_id':44,'medio':'TARJETA'},headers={'Authorization':'Bearer token-de-laura','Accept-Language':'en'})
    assert respuesta.status_code==409
    assert 'confirmed' in respuesta.json['error']['mensaje']
    assert 'confirmada' not in respuesta.json['error']['mensaje']
