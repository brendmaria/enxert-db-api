
#!/usr/bin/env python3
"""
Enxert.DB - Interface Python v5
===============================
Gerencia o banco Enxert.DB (SQLite).

O que mudou em relacao a v4 (todos os itens foram reproduzidos antes de corrigir):
- Nunca apaga o banco do usuario. Se o arquivo existente tiver estrutura
  incompativel, ele e RENOMEADO (enxert.db.bak-AAAAMMDD-HHMMSS) e um banco novo
  e criado. (v4 fazia os.remove e perdia os cadastros.)
- Tabelas que faltam sao criadas (v4 so olhava a coluna papel_agronomico e
  quebrava com "no such table" em bancos parciais).
- Chaves estrangeiras passam a ser validadas (PRAGMA foreign_keys=ON). Antes o
  menu 5 aceitava IDs de planta que nao existem.
- Mesmo par copa x porta-enxerto x metodo nao pode ser cadastrado duas vezes.
- Entradas invalidas pedem de novo, em vez de virar "Compativel / 0%" em silencio.
- Copa e porta-enxerto nao podem ser a mesma planta.
- O enxert_db.sql agora pode ser executado varias vezes (INSERT OR IGNORE) e nao
  tem BEGIN/COMMIT, que dao "cannot start a transaction within a transaction"
  quando o .sql e executado dentro de uma transacao ja aberta.
- TaxID do tomate corrigido: 3649 e Carica papaya; Solanum lycopersicum = 4081.

Se 'enxert_db.sql' nao estiver ao lado deste arquivo, usa o SQL embutido no fim
deste script (mesmo conteudo).
"""

import os
import sqlite3
import sys
from datetime import datetime

# Evita UnicodeEncodeError com emojis em terminais Windows antigos / saida redirecionada.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "enxert.db")
SQL_FILE = os.path.join(BASE_DIR, "enxert_db.sql")

STATUS_VALIDOS = [
    "Compatível",
    "Incompatibilidade Localizada",
    "Incompatibilidade Translocada",
    "Incompatível",
]

# Colunas que cada tabela precisa ter para o programa funcionar.
ESTRUTURA_ESPERADA = {
    "Plantas": {"id_planta", "nome_comum", "nome_cientifico", "ncbi_taxid", "familia", "genero", "papel_agronomico"},
    "Metodos_Enxertia": {"id_metodo", "nome_metodo", "descricao", "tempo_cicatrizacao_dias"},
    "Compatibilidade": {"id_compatibilidade", "id_copa", "id_porta_enxerto", "status_compatibilidade",
                        "taxa_pegamento_pct", "id_metodo", "observacoes"},
    "Biomarcadores": {"id_biomarcador", "id_planta", "atividade_peroxidase", "concentracao_fenois",
                      "presenca_prunasina", "acoplamento_plasmodesmal"},
    "Atributos_Resistencia": {"id_atributo", "id_porta_enxerto", "resistencia_patogenos_solo",
                              "resistencia_doencas_parte_aerea", "tolerancia_estresse_abiotico",
                              "efeito_porte_vigor"},
}

_banco_pronto = False


# ---------------------------------------------------------------------------
# Banco: preparo e conexao
# ---------------------------------------------------------------------------

def _estrutura_compativel(caminho):
    """True se todas as tabelas EXISTENTES tem as colunas esperadas.
    Tabelas ausentes nao contam como incompativeis: serao criadas."""
    con = sqlite3.connect(caminho)
    try:
        for tabela, colunas in ESTRUTURA_ESPERADA.items():
            existentes = {l[1] for l in con.execute(f"PRAGMA table_info({tabela})")}
            if existentes and not colunas.issubset(existentes):
                return False
        return True
    except sqlite3.DatabaseError:
        return False  # arquivo corrompido / nao e um SQLite
    finally:
        con.close()


def _guardar_backup(caminho):
    destino = f"{caminho}.bak-{datetime.now():%Y%m%d-%H%M%S}"
    os.replace(caminho, destino)
    return destino


def _executar_sql(con, sql_texto):
    """Executa um script SQL de forma atomica: ou entra tudo, ou nada."""
    try:
        con.executescript("BEGIN;\n" + sql_texto + "\nCOMMIT;")
    except Exception:
        if con.in_transaction:
            con.rollback()
        raise


def _preparar_banco():
    global _banco_pronto
    if _banco_pronto:
        return

    if os.path.exists(DB_FILE) and not _estrutura_compativel(DB_FILE):
        try:
            destino = _guardar_backup(DB_FILE)
            print(f"⚠️ O arquivo 'enxert.db' existente tem estrutura incompatível. "
                  f"Foi preservado como '{os.path.basename(destino)}' e um banco novo será criado.")
        except OSError as e:
            sys.exit(f"❌ Não consegui preservar o 'enxert.db' antigo ({e}). "
                     f"Feche outros programas que o estejam usando e tente de novo.")

    con = sqlite3.connect(DB_FILE)
    try:
        sql_texto = SQL_EMBUTIDO
        if os.path.exists(SQL_FILE):
            try:
                with open(SQL_FILE, "r", encoding="utf-8-sig") as f:
                    sql_texto = f.read()
            except (OSError, UnicodeDecodeError) as e:
                print(f"⚠️ Não consegui ler 'enxert_db.sql' ({e}). Usando o SQL embutido.")

        # 1) estrutura (idempotente). Se o .sql estiver quebrado, cai no embutido.
        # 2) dados iniciais so entram se o catalogo estiver vazio.
        vazio = _catalogo_vazio(con)
        try:
            _executar_sql(con, sql_texto if vazio else _so_estrutura(sql_texto))
        except Exception as e:
            print(f"⚠️ Erro ao aplicar 'enxert_db.sql': {e}. Usando o SQL embutido.")
            try:
                _executar_sql(con, SQL_EMBUTIDO if vazio else _so_estrutura(SQL_EMBUTIDO))
            except Exception as e2:
                sys.exit(f"❌ Não foi possível preparar o banco: {e2}\n"
                         f"   (se for 'UNIQUE', o banco já tem combinações duplicadas: remova as repetidas e tente de novo)")
        if vazio:
            print("✅ Banco Enxert.DB inicializado com os dados iniciais.")
    finally:
        con.close()
    _banco_pronto = True


def _catalogo_vazio(con):
    try:
        return con.execute("SELECT COUNT(*) FROM Plantas").fetchone()[0] == 0
    except sqlite3.OperationalError:  # tabela ainda nao existe
        return True


def _so_estrutura(sql_texto):
    """Mantem CREATE TABLE/INDEX e descarta os INSERTs."""
    comandos = [c.strip() for c in _dividir_comandos(sql_texto)]
    return ";\n".join(c for c in comandos if c.upper().startswith("CREATE")) + ";"


def _dividir_comandos(sql_texto):
    comandos, atual = [], []
    for linha in sql_texto.splitlines():
        if linha.strip().startswith("--"):
            continue
        atual.append(linha)
        if sqlite3.complete_statement("\n".join(atual)):
            comandos.append("\n".join(atual))
            atual = []
    return comandos


def get_connection():
    _preparar_banco()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")  # sem isso o SQLite ignora as FOREIGN KEY
    return conn


# ---------------------------------------------------------------------------
# Entrada de dados
# ---------------------------------------------------------------------------

def ler_int(prompt):
    try:
        return int(input(prompt).strip())
    except ValueError:
        print("❌ Digite um número inteiro.")
        return None


def ler_opcao(prompt, validas):
    """Repete ate o usuario digitar uma opcao valida (ou deixar vazio p/ cancelar)."""
    while True:
        v = input(prompt).strip()
        if v == "":
            return None
        if v in validas:
            return v
        print(f"❌ Opção inválida. Escolha entre: {', '.join(validas)} (ou Enter para cancelar).")


def ler_taxa():
    while True:
        v = input("Taxa de pegamento esperada % (0 a 100, ex: 95.0): ").strip().replace(",", ".")
        try:
            taxa = float(v)
        except ValueError:
            print("❌ Digite um número (ex: 95.0).")
            continue
        if 0 <= taxa <= 100:
            return taxa
        print("❌ A taxa precisa estar entre 0 e 100.")


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def _fmt_taxa(valor):
    return "não informada" if valor is None else f"{valor}%"


def listar_plantas(filtro_papel=None):
    conn = get_connection()
    try:
        if filtro_papel is not None:
            plantas = conn.execute("""
                SELECT id_planta, nome_comum, nome_cientifico, familia, papel_agronomico
                FROM Plantas
                WHERE papel_agronomico = ? OR papel_agronomico = 'Ambos'
                ORDER BY id_planta
            """, (filtro_papel,)).fetchall()
        else:
            plantas = conn.execute("""
                SELECT id_planta, nome_comum, nome_cientifico, familia, papel_agronomico
                FROM Plantas ORDER BY id_planta
        """).fetchall()
    finally:
        conn.close()

    print("\n" + "=" * 92)
    print("CATÁLOGO DE PLANTAS CADASTRADAS NO ENXERT.DB")
    print("=" * 92)
    print(f"{'ID':<4} | {'Nome Comum':<32} | {'Nome Científico':<50} | Papel")
    print("-" * 92)
    for p in plantas:
        print(f"{p[0]:<4} | {p[1]:<32} | {p[2]:<50} | {p[4]}")
    print("=" * 92 + "\n")


def _planta(conn, id_planta):
    return conn.execute(
        "SELECT nome_comum, nome_cientifico FROM Plantas WHERE id_planta = ?", (id_planta,)
    ).fetchone()


def _imprimir_resultados(resultados, icone, vazio):
    if not resultados:
        print(vazio)
        return
    for r in resultados:
        print(f"{icone} {r[0]} ({r[1]})")
        print(f"   • Status: {r[2]}")
        print(f"   • Taxa de Pegamento: {_fmt_taxa(r[3])}")
        print(f"   • Método Recomendado: {r[4] or 'Não especificado'}")
        print(f"   • Observações: {r[5] or '—'}")
        print("-" * 80)


def buscar_porta_enxertos_para_copa(id_copa):
    conn = get_connection()
    try:
        copa = _planta(conn, id_copa)
        if not copa:
            print("❌ Planta não encontrada!")
            return
        print("\n" + "=" * 80)
        print(f"RECOMENDAÇÕES DE PORTA-ENXERTO PARA A COPA: {copa[0]} ({copa[1]})")
        print("=" * 80)
        resultados = conn.execute("""
            SELECT p.nome_comum, p.nome_cientifico, c.status_compatibilidade,
                   c.taxa_pegamento_pct, m.nome_metodo, c.observacoes
            FROM Compatibilidade c
            JOIN Plantas p ON c.id_porta_enxerto = p.id_planta
            LEFT JOIN Metodos_Enxertia m ON c.id_metodo = m.id_metodo
            WHERE c.id_copa = ?
            ORDER BY c.taxa_pegamento_pct DESC
        """, (id_copa,)).fetchall()
    finally:
        conn.close()
    _imprimir_resultados(resultados, "🌱 Porta-Enxerto:",
                         "⚠️ Nenhuma combinação registrada ainda para esta planta como enxerto (copa).")


def buscar_copas_para_porta_enxerto(id_pe):
    conn = get_connection()
    try:
        pe = _planta(conn, id_pe)
        if not pe:
            print("❌ Planta não encontrada!")
            return
        print("\n" + "=" * 80)
        print(f"COPAS (ENXERTOS) COMPATÍVEIS PARA O PORTA-ENXERTO: {pe[0]} ({pe[1]})")
        print("=" * 80)
        resultados = conn.execute("""
            SELECT p.nome_comum, p.nome_cientifico, c.status_compatibilidade,
                   c.taxa_pegamento_pct, m.nome_metodo, c.observacoes
            FROM Compatibilidade c
            JOIN Plantas p ON c.id_copa = p.id_planta
            LEFT JOIN Metodos_Enxertia m ON c.id_metodo = m.id_metodo
            WHERE c.id_porta_enxerto = ?
            ORDER BY c.taxa_pegamento_pct DESC
        """, (id_pe,)).fetchall()
    finally:
        conn.close()
    _imprimir_resultados(resultados, "🍎 Enxerto/Copa:",
                         "⚠️ Nenhuma copa registrada ainda para este porta-enxerto.")


# ---------------------------------------------------------------------------
# Cadastros
# ---------------------------------------------------------------------------

def cadastrar_planta():
    print("\n--- CADASTRO DE NOVA PLANTA NO CATÁLOGO ---")
    nome_comum = input("Nome Comum (ex: Maracujá Doce): ").strip()
    nome_cientifico = input("Nome Científico (ex: Passiflora alata): ").strip()
    taxid = input("NCBI TaxID (opcional, Enter se não tiver): ").strip()
    familia = input("Família Botânica (ex: Passifloraceae): ").strip()
    genero = input("Gênero Botânico (ex: Passiflora): ").strip()

    faltando = [n for n, v in [("Nome Comum", nome_comum), ("Nome Científico", nome_cientifico),
                               ("Família", familia), ("Gênero", genero)] if not v]
    if faltando:
        print(f"❌ Campos obrigatórios em branco: {', '.join(faltando)}. Nada foi cadastrado.")
        return
    if taxid and not taxid.isdigit():
        print("❌ O TaxID precisa ser um número (ou deixe em branco). Nada foi cadastrado.")
        return
    taxid_val = int(taxid) if taxid else None

    print("Selecione o papel agronômico habitual:")
    print("1. Enxerto (Copa)\n2. Porta-Enxerto\n3. Ambos")
    op = ler_opcao("Opção (1-3) [Enter = Ambos]: ", ["1", "2", "3"])
    papel = {"1": "Enxerto", "2": "Porta-Enxerto", "3": "Ambos", None: "Ambos"}[op]

    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO Plantas (nome_comum, nome_cientifico, ncbi_taxid, familia, genero, papel_agronomico)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome_comum, nome_cientifico, taxid_val, familia, genero, papel))
        conn.commit()
        print(f"✅ Planta '{nome_comum}' cadastrada com sucesso! (ID: {cur.lastrowid})")
    except sqlite3.IntegrityError:
        print(f"❌ Já existe uma planta com o nome científico '{nome_cientifico}'.")
    finally:
        conn.close()


def _listar_metodos():
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id_metodo, nome_metodo, tempo_cicatrizacao_dias FROM Metodos_Enxertia ORDER BY id_metodo"
        ).fetchall()
    finally:
        conn.close()


def cadastrar_compatibilidade():
    listar_plantas()
    print("--- VINCULAR ENXERTO E PORTA-ENXERTO ---")
    id_copa = ler_int("ID da planta que atuará como ENXERTO (Copa): ")
    if id_copa is None:
        return
    id_pe = ler_int("ID da planta que atuará como PORTA-ENXERTO: ")
    if id_pe is None:
        return
    if id_copa == id_pe:
        print("❌ Copa e porta-enxerto não podem ser a mesma planta.")
        return

    conn = get_connection()
    try:
        copa, pe = _planta(conn, id_copa), _planta(conn, id_pe)
    finally:
        conn.close()
    if not copa or not pe:
        print(f"❌ ID inexistente no catálogo ({'copa' if not copa else 'porta-enxerto'}). Nada foi gravado.")
        return
    print(f"→ {copa[0]} ({copa[1]})  sobre  {pe[0]} ({pe[1]})")

    print("\nStatus de Compatibilidade:")
    for i, s in enumerate(STATUS_VALIDOS, 1):
        print(f"{i}. {s}")
    op = ler_opcao("Escolha (1-4, Enter cancela): ", [str(i) for i in range(1, 5)])
    if op is None:
        print("Cancelado.")
        return
    status = STATUS_VALIDOS[int(op) - 1]

    taxa = ler_taxa()

    print("\nMétodo de enxertia:")
    metodos = _listar_metodos()
    for m in metodos:
        print(f"{m[0]}. {m[1]} ({m[2]} dias)")
    ids_metodo = [str(m[0]) for m in metodos]
    op_m = ler_opcao("Escolha o método (Enter = não especificado): ", ids_metodo)
    id_metodo = int(op_m) if op_m else None

    obs = input("Observações técnicas: ").strip() or None

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO Compatibilidade
                (id_copa, id_porta_enxerto, status_compatibilidade, taxa_pegamento_pct, id_metodo, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_copa, id_pe, status, taxa, id_metodo, obs))
        conn.commit()
        print("✅ Relação de compatibilidade gravada com sucesso!")
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            print("❌ Esse par (copa × porta-enxerto × método) já está cadastrado.")
        else:
            print(f"❌ Não foi possível gravar: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def menu_principal():
    while True:
        print("\n" + "=" * 50)
        print("     SISTEMA ENXERT.DB - GERENCIADOR DE ENXERTIA")
        print("=" * 50)
        print("1. Listar todas as plantas cadastradas")
        print("2. Buscar Porta-Enxertos para um Enxerto (Copa)")
        print("3. Buscar Enxertos (Copas) para um Porta-Enxerto")
        print("4. Cadastrar nova Planta no Catálogo")
        print("5. Cadastrar relação de Compatibilidade (Copa x Porta-Enxerto)")
        print("6. Sair")
        print("=" * 50)
        try:
            opcao = input("Escolha uma opção (1-6): ").strip()
        except EOFError:
            break

        if opcao == "1":
            listar_plantas()

        elif opcao == "2":
            listar_plantas(filtro_papel='Enxerto')
            id_c = ler_int("Digite o ID da planta Enxerto/Copa: ")
            if id_c is not None:
                buscar_porta_enxertos_para_copa(id_c)

        elif opcao == "3":
            listar_plantas(filtro_papel='Porta-Enxerto')
            id_p = ler_int("Digite o ID do Porta-Enxerto: ")
            if id_p is not None:
                buscar_copas_para_porta_enxerto(id_p)

        elif opcao == "4":
            cadastrar_planta()

        elif opcao == "5":
            cadastrar_compatibilidade()

        elif opcao == "6":
            print("Encerrando o Enxert.DB. Até logo!")
            break
        else:
            print("❌ Opção inválida, tente novamente.")


# SQL embutido: copia exata de enxert_db.sql (usado se o arquivo nao estiver ao lado).
SQL_EMBUTIDO = r'''-- Enxert.DB -- pode ser executado varias vezes (INSERT OR IGNORE / IF NOT EXISTS).
-- Sem BEGIN/COMMIT: quem executa o script controla a transacao.

CREATE TABLE IF NOT EXISTS Plantas (
    id_planta INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_comum TEXT NOT NULL,
    nome_cientifico TEXT NOT NULL UNIQUE,
    ncbi_taxid INTEGER,
    familia TEXT NOT NULL,
    genero TEXT NOT NULL,
    papel_agronomico TEXT CHECK(papel_agronomico IN ('Enxerto', 'Porta-Enxerto', 'Ambos'))
);

CREATE TABLE IF NOT EXISTS Metodos_Enxertia (
    id_metodo INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_metodo TEXT NOT NULL,
    descricao TEXT,
    tempo_cicatrizacao_dias INTEGER
);

CREATE TABLE IF NOT EXISTS Compatibilidade (
    id_compatibilidade INTEGER PRIMARY KEY AUTOINCREMENT,
    id_copa INTEGER NOT NULL,
    id_porta_enxerto INTEGER NOT NULL,
    status_compatibilidade TEXT CHECK(status_compatibilidade IN ('Compatível', 'Incompatibilidade Localizada', 'Incompatibilidade Translocada', 'Incompatível')),
    taxa_pegamento_pct REAL,
    id_metodo INTEGER,
    observacoes TEXT,
    FOREIGN KEY(id_copa) REFERENCES Plantas(id_planta),
    FOREIGN KEY(id_porta_enxerto) REFERENCES Plantas(id_planta),
    FOREIGN KEY(id_metodo) REFERENCES Metodos_Enxertia(id_metodo)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_compatibilidade_par
    ON Compatibilidade(id_copa, id_porta_enxerto, COALESCE(id_metodo, 0));

CREATE TABLE IF NOT EXISTS Biomarcadores (
    id_biomarcador INTEGER PRIMARY KEY AUTOINCREMENT,
    id_planta INTEGER NOT NULL,
    atividade_peroxidase TEXT,
    concentracao_fenois TEXT,
    presenca_prunasina BOOLEAN,
    acoplamento_plasmodesmal TEXT,
    FOREIGN KEY(id_planta) REFERENCES Plantas(id_planta)
);

CREATE TABLE IF NOT EXISTS Atributos_Resistencia (
    id_atributo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_porta_enxerto INTEGER NOT NULL,
    resistencia_patogenos_solo TEXT,
    resistencia_doencas_parte_aerea TEXT,
    tolerancia_estresse_abiotico TEXT,
    efeito_porte_vigor TEXT,
    FOREIGN KEY(id_porta_enxerto) REFERENCES Plantas(id_planta)
);

-- ATENCAO: ncbi_taxid das linhas 4, 8 e 11 (hibridos) e das linhas 2, 3, 7 e 9
-- nao foi conferido contra o NCBI -- revisar antes de usar em apresentacao.
-- Inserções Plantas
INSERT OR IGNORE INTO "Plantas" VALUES(1,'Tomateiro Janaína','Solanum lycopersicum',4081,'Solanaceae','Solanum','Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(2,'Jurubeba','Solanum paniculatum',4102,'Solanaceae','Solanum','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(3,'Joá','Solanum aculeatissimum',110275,'Solanaceae','Solanum','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(4,'Porta-Enxerto Castelpro','Solanum lycopersicum x S. habrochaites (Castelpro)',4081,'Solanaceae','Solanum','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(5,'Porta-Enxerto 15PEX00056','Solanum lycopersicum (15PEX00056)',4081,'Solanaceae','Solanum','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(6,'Laranjeira Pera D6','Citrus sinensis (Pera D6)',2711,'Rutaceae','Citrus','Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(7,'Tangerineira Sunki Tropical','Citrus sunki',555021,'Rutaceae','Citrus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(8,'Citrandarin San Diego','Citrus sunki x Poncirus trifoliata',2711,'Rutaceae','Citrus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(9,'Limoeiro Cravo','Citrus limonia',170929,'Rutaceae','Citrus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(10,'Pessegueiro Santa Rosa / Diamante','Prunus persica',3760,'Rosaceae','Prunus','Ambos');
INSERT OR IGNORE INTO "Plantas" VALUES(11,'Ameixeira Marianna','Prunus marianna',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(12,'Ameixeira Mirabolano','Prunus cerasifera',3765,'Rosaceae','Prunus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(13,'Pessegueiro Okinawa','Prunus persica (Okinawa)',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(14,'Pessegueiro Capdeboscq','Prunus persica (Capdeboscq)',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(15,'Melancia','Citrullus lanatus',3654,'Cucurbitaceae','Citrullus','Enxerto');
INSERT OR IGNORE INTO "Plantas" VALUES(16,'Abóbora / Porongo','Cucurbita maxima',3661,'Cucurbitaceae','Cucurbita','Porta-Enxerto');

-- Inserções Métodos
INSERT OR IGNORE INTO "Metodos_Enxertia" VALUES(1,'Garfagem de Topo / Fenda-Cheia','União por fenda no porta-enxerto com garfo cortado em cunha no enxerto.',14);
INSERT OR IGNORE INTO "Metodos_Enxertia" VALUES(2,'Borbulhia T-Invertido','Inserção de uma gema vegetativa sob a casca cortada em forma de T invertido no porta-enxerto.',12);
INSERT OR IGNORE INTO "Metodos_Enxertia" VALUES(3,'Enxertia por Aproximação','União física dos caules mantendo ambas as plantas com raízes até a cicatrização.',15);
INSERT OR IGNORE INTO "Metodos_Enxertia" VALUES(4,'Perfuração Apical','Remoção do meristema do porta-enxerto e inserção do hipocótilo perfurado do enxerto.',10);

-- Inserções Compatibilidade
INSERT OR IGNORE INTO "Compatibilidade" VALUES(1,1,5,'Compatível',100.0,1,'Excelente pegamento, aumento significativo na massa média dos frutos e produtividade total.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(2,1,4,'Compatível',95.8,1,'Ótimo equilíbrio vegetativo/produtivo e alta compatibilidade cambial.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(3,1,2,'Compatível',94.1,1,'Alta taxa de sobrevivência, útil contra Ralstonia solanacearum, porém reduz ligeiramente diâmetro/massa de frutos.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(4,1,3,'Compatível',96.6,1,'Boa taxa de pegamento, mas inibe enchimento de frutos e reduz produtividade comercial.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(5,6,7,'Compatível',100.0,2,'Superior desenvolvimento inicial, maior número de folhas e altura da muda.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(6,6,8,'Compatível',95.0,2,'Bom desenvolvimento vegetativo inicial e vigor equilibrado.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(7,10,13,'Compatível',90.0,1,'Evolução cambial harmônica, níveis similares de peroxidase entre copa e cavalo.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(8,10,11,'Incompatibilidade Translocada',0.0,1,'Incompatibilidade severa por translocação de compostos e alta atividade de peroxidase/fenóis.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(9,10,12,'Incompatibilidade Translocada',0.0,1,'Falha de brotação dos enxertos decorrente do estresse oxidativo e acúmulo fenólico.');
INSERT OR IGNORE INTO "Compatibilidade" VALUES(10,15,16,'Compatível',98.0,4,'Excelente resistência a Fusarium de solo, baixa temperatura e excesso de umidade.');

-- Inserções Biomarcadores
INSERT OR IGNORE INTO "Biomarcadores" VALUES(1,10,'Média / Balanceada','Normal / Estável',0,'Funcional');
INSERT OR IGNORE INTO "Biomarcadores" VALUES(2,11,'Elevada','Muito Alta',1,'Deficiente / Não funcional');
INSERT OR IGNORE INTO "Biomarcadores" VALUES(3,12,'Elevada','Muito Alta',1,'Deficiente / Não funcional');
INSERT OR IGNORE INTO "Biomarcadores" VALUES(4,13,'Parecida com enxerto','Equilibrada',0,'Funcional');

-- Inserções Resistências
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(1,2,'Resistente a Ralstonia solanacearum e fungos de solo','N/A','Resistente à seca','Vigoroso / Rústico');
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(2,5,'Resistente a murcha bacteriana e Fusarium','N/A','Alta eficiência hídrica','Equilibrado / Produtivo');
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(3,7,'Resistente a Phytophthora citrophthora (Gomose)','Memória de defesa (Priming)','Tolerante à seca','Vigoroso');
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(4,9,'Sensível à gomose em solos úmidos','N/A','Tolerante à seca','Vigoroso');
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(5,13,'Resistente aos nematoides Meloidogyne incognita e M. javanica','N/A','Adequada ancoragem radicular','Vigoroso');
INSERT OR IGNORE INTO "Atributos_Resistencia" VALUES(6,16,'Resistente à fusariose e patógenos de solo','N/A','Resistente ao excesso de umidade e frio','Ananicante a Médio');

'''


if __name__ == "__main__":
    menu_principal()
