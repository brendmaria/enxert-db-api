from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
import sqlite3
import os

app = FastAPI(
    title="Enxert.DB API - Arquitetura de APIs",
    description="API REST desenvolvida para otimizar pesquisas de compatibilidade de plantas para enxertia (Atividade Prática 3).",
    version="1.0.0"
)

# Chave simples para simular o recurso de segurança exigido no trabalho
API_KEY = "enxert_secure_2026"
api_key_header = APIKeyHeader(name="X-API-Key")

def verificar_seguranca(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Chave de API inválida ou ausente."
        )
    return api_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "enxert.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", summary="Raiz da API")
def raiz():
    return {"mensagem": "API do Enxert.DB a funcionar com sucesso para a Atividade Prática 3!"}

@app.get("/plantas", summary="Listar todas as plantas cadastradas")
def listar_plantas():
    conn = get_db()
    cursor = conn.execute("SELECT id_planta, nome_comum, nome_cientifico, familia, genero, papel_agronomico FROM Plantas")
    plantas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return plantas

@app.get("/compatibilidade/copa/{id_copa}", summary="Consultar porta-enxertos compatíveis por ID da copa")
def buscar_compatibilidade(id_copa: int):
    conn = get_db()
    query = """
        SELECT p.nome_comum AS porta_enxerto, p.nome_cientifico, c.status_compatibilidade,
               c.taxa_pegamento_pct, c.observacoes
        FROM Compatibilidade c
        JOIN Plantas p ON c.id_porta_enxerto = p.id_planta
        WHERE c.id_copa = ?
    """
    cursor = conn.execute(query, (id_copa,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    if not resultados:
        raise HTTPException(status_code=404, detail="Nenhuma compatibilidade encontrada para esta copa.")
    return resultados

@app.get("/seguro/dados-protegidos", summary="Rota protegida por chave de API (Segurança)")
def dados_protegidos(token: str = Security(verificar_seguranca)):
    return {"status": "Autorizado", "detalhe": "Acedeu com sucesso a um recurso protegido por política de segurança de API."}