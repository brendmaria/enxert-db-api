#!/usr/bin/env python3
"""
Enxert.DB - Módulo de Automação e Cruzamento de Culturas
========================================================
"""

import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "enxert.db")
SQL_FILE = os.path.join(BASE_DIR, "enxert_db.sql")

TAXONOMIA_CONHECIDA = {
    "solanum lycopersicum": {"familia": "Solanaceae", "genero": "Solanum", "taxid": 3649, "nome_comum": "Tomateiro"},
    "solanum paniculatum": {"familia": "Solanaceae", "genero": "Solanum", "taxid": 4102, "nome_comum": "Jurubeba"},
    "solanum aculeatissimum": {"familia": "Solanaceae", "genero": "Solanum", "taxid": 110275, "nome_comum": "Joá"},
    "solanum melongena": {"familia": "Solanaceae", "genero": "Solanum", "taxid": 4110, "nome_comum": "Berinjela"},
    "citrus sinensis": {"familia": "Rutaceae", "genero": "Citrus", "taxid": 2711, "nome_comum": "Laranjeira Doce"},
    "citrus sunki": {"familia": "Rutaceae", "genero": "Citrus", "taxid": 555021, "nome_comum": "Tangerineira Sunki"},
    "citrus limonia": {"familia": "Rutaceae", "genero": "Citrus", "taxid": 170929, "nome_comum": "Limoeiro Cravo"},
    "prunus persica": {"familia": "Rosaceae", "genero": "Prunus", "taxid": 3760, "nome_comum": "Pessegueiro"},
    "prunus marianna": {"familia": "Rosaceae", "genero": "Prunus", "taxid": 3760, "nome_comum": "Ameixeira Marianna"},
    "prunus cerasifera": {"familia": "Rosaceae", "genero": "Prunus", "taxid": 3765, "nome_comum": "Ameixeira Mirabolano"},
    "citrullus lanatus": {"familia": "Cucurbitaceae", "genero": "Citrullus", "taxid": 3654, "nome_comum": "Melancia"},
    "cucurbita maxima": {"familia": "Cucurbitaceae", "genero": "Cucurbita", "taxid": 3661, "nome_comum": "Abóbora / Porongo"}
}

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Plantas'")
    if not cursor.fetchone():
        if os.path.exists(SQL_FILE):
            with open(SQL_FILE, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS Plantas (
                    id_planta INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_comum TEXT NOT NULL,
                    nome_cientifico TEXT NOT NULL UNIQUE,
                    ncbi_taxid INTEGER,
                    familia TEXT NOT NULL,
                    genero TEXT NOT NULL,
                    papel_agronomico TEXT CHECK(papel_agronomico IN ('Enxerto', 'Porta-Enxerto', 'Ambos'))
                );
                CREATE TABLE IF NOT EXISTS Compatibilidade (
                    id_compatibilidade INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_copa INTEGER NOT NULL,
                    id_porta_enxerto INTEGER NOT NULL,
                    status_compatibilidade TEXT,
                    taxa_pegamento_pct REAL,
                    id_metodo INTEGER,
                    observacoes TEXT
                );
            """)
            conn.commit()
    return conn

def inferir_taxonomia(nome_cientifico):
    key = nome_cientifico.lower().strip()
    if key in TAXONOMIA_CONHECIDA:
        return TAXONOMIA_CONHECIDA[key]
    partes = nome_cientifico.strip().split()
    genero = partes[0].capitalize() if partes else "Desconhecido"
    return {
        "familia": "Desconhecida",
        "genero": genero,
        "taxid": None,
        "nome_comum": nome_cientifico.capitalize()
    }

def analisar_compatibilidade(tax_copa, tax_pe):
    gen_copa = tax_copa["genero"].lower()
    gen_pe = tax_pe["genero"].lower()
    fam_copa = tax_copa["familia"].lower()
    fam_pe = tax_pe["familia"].lower()

    if gen_copa != "desconhecido" and gen_copa == gen_pe:
        return "Compatível", 95.0, f"Alta afinidade taxonômica (Mesmo Gênero: {tax_copa['genero']}). Elevada cicatrização cambial."
    elif fam_copa != "desconhecida" and fam_copa == fam_pe:
        return "Compatível", 85.0, f"Afinidade moderada (Mesma Família Botânica: {tax_copa['familia']}). Recomendada avaliação prévia de fenóis."
    else:
        return "Incompatível", 0.0, f"Divergência taxonômica (Famílias distintas: {tax_copa['familia']} x {tax_pe['familia']}). Risco de necrose."

def automatizar_relacao(nome_copa, nome_pe, papel_copa="Enxerto", papel_pe="Porta-Enxerto"):
    conn = get_connection()
    cursor = conn.cursor()

    info_copa = inferir_taxonomia(nome_copa)
    info_pe = inferir_taxonomia(nome_pe)

    cursor.execute("SELECT id_planta FROM Plantas WHERE LOWER(nome_cientifico) = LOWER(?)", (nome_copa,))
    row_copa = cursor.fetchone()
    if row_copa:
        id_copa = row_copa[0]
    else:
        cursor.execute("INSERT INTO Plantas (nome_comum, nome_cientifico, ncbi_taxid, familia, genero, papel_agronomico) VALUES (?, ?, ?, ?, ?, ?)", (info_copa["nome_comum"], nome_copa, info_copa["taxid"], info_copa["familia"], info_copa["genero"], papel_copa))
        id_copa = cursor.lastrowid
        print(f"✅ Planta Copa \"{nome_copa}\" registrada no catálogo (ID: {id_copa}).")

    cursor.execute("SELECT id_planta FROM Plantas WHERE LOWER(nome_cientifico) = LOWER(?)", (nome_pe,))
    row_pe = cursor.fetchone()
    if row_pe:
        id_pe = row_pe[0]
    else:
        cursor.execute("INSERT INTO Plantas (nome_comum, nome_cientifico, ncbi_taxid, familia, genero, papel_agronomico) VALUES (?, ?, ?, ?, ?, ?)", (info_pe["nome_comum"], nome_pe, info_pe["taxid"], info_pe["familia"], info_pe["genero"], papel_pe))
        id_pe = cursor.lastrowid
        print(f"✅ Planta Porta-Enxerto \"{nome_pe}\" registrada no catálogo (ID: {id_pe}).")

    status, pegamento, obs = analisar_compatibilidade(info_copa, info_pe)

    cursor.execute("SELECT id_compatibilidade FROM Compatibilidade WHERE id_copa = ? AND id_porta_enxerto = ?", (id_copa, id_pe))
    row_rel = cursor.fetchone()

    if row_rel:
        cursor.execute("UPDATE Compatibilidade SET status_compatibilidade = ?, taxa_pegamento_pct = ?, observacoes = ? WHERE id_compatibilidade = ?", (status, pegamento, obs, row_rel[0]))
        print(f"🔄 Relação de compatibilidade atualizada (ID: {row_rel[0]}).")
    else:
        cursor.execute("INSERT INTO Compatibilidade (id_copa, id_porta_enxerto, status_compatibilidade, taxa_pegamento_pct, observacoes) VALUES (?, ?, ?, ?, ?)", (id_copa, id_pe, status, pegamento, obs))
        print(f"🎉 Nova relação de compatibilidade cadastrada entre {nome_copa} (Copa) e {nome_pe} (Porta-Enxerto)!")

    conn.commit()
    conn.close()

def processar_lote_automatico():
    pairs = [
        ("Solanum paniculatum", "Solanum lycopersicum"), # Jurubeba como copa em tomateiro
        ("Solanum melongena", "Solanum paniculatum"),   # Berinjela sobre Jurubeba
        ("Citrullus lanatus", "Cucurbita maxima"),     # Melancia sobre Abóbora
        ("Citrus sinensis", "Citrus limonia")          # Laranjeira sobre Limoeiro Cravo
    ]
    print("🔄 Processando lote automático de cruzamento de culturas...")
    for c, p in pairs:
        automatizar_relacao(c, p)

if __name__ == "__main__":
    print("="*75)
    print("      ENXERT.DB - MÓDULO DE AUTOMAÇÃO E CRUZAMENTO DE CULTURAS")
    print("="*75)
    if len(sys.argv) >= 3:
        copa = sys.argv[1]
        pe = sys.argv[2]
        automatizar_relacao(copa, pe)
    elif len(sys.argv) == 2 and sys.argv[1] == "--batch":
        processar_lote_automatico()
    else:
        print("Modo Interativo de Cruzamento Autônomo:")
        c = input("Nome científico da COPA (ex: Solanum paniculatum): ").strip()
        p = input("Nome científico do PORTA-ENXERTO (ex: Solanum lycopersicum): ").strip()
        if c and p:
            automatizar_relacao(c, p)
