from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_rota_raiz():
    response = client.get("/")
    assert response.status_code == 200
    assert "Enxert.DB" in response.json()["mensagem"]

def test_listar_plantas():
    response = client.get("/plantas")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_seguranca_negada():
    # Tenta aceder à rota protegida sem enviar a chave de API
    response = client.get("/seguro/dados-protegidos")
    assert response.status_code == 401

def test_seguranca_permitida():
    # Acede à rota protegida enviando a chave correta no cabeçalho
    response = client.get("/seguro/dados-protegidos", headers={"X-API-Key": "enxert_secure_2026"})
    assert response.status_code == 200
    assert response.json()["status"] == "Autorizado"