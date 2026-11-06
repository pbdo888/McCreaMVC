"""
Acesso ao banco de dados SQLite.

Este módulo é a única parte do projeto que abre conexões com o banco. Os models
(Usuario, Maquina, Cupom...) chamam conectar() e escrevem o SQL de cada tabela.
"""
import sqlite3
from contextlib import contextmanager

# Caminho do arquivo do banco. O app.py troca pelo valor do Config com configurar().
_caminho_banco = "mccrea_mvc.db"

# Estrutura das tabelas. "IF NOT EXISTS" permite rodar este script toda vez que o app inicia.
# As datas são gravadas no horário do computador: datetime('now', 'localtime').
ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL,
  nascimento TEXT NOT NULL,
  sexo TEXT NOT NULL,
  estado_civil TEXT NOT NULL,
  telefone TEXT NOT NULL,
  moradores INTEGER NOT NULL,
  como_conheceu TEXT,
  aceita_ofertas INTEGER NOT NULL DEFAULT 0,
  cep TEXT NOT NULL,
  logradouro TEXT NOT NULL,
  numero TEXT NOT NULL,
  complemento TEXT,
  bairro TEXT NOT NULL,
  cidade TEXT NOT NULL,
  uf TEXT NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  pontos INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS maquinas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  endereco TEXT,
  bairro TEXT,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  capacidade INTEGER NOT NULL DEFAULT 500,
  ocupacao INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'manutencao', 'inativa'))
);
CREATE TABLE IF NOT EXISTS cupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  marca TEXT NOT NULL,
  descricao TEXT NOT NULL,
  custo INTEGER NOT NULL CHECK (custo > 0),
  ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS depositos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
  material TEXT NOT NULL,
  quantidade INTEGER NOT NULL,
  pontos INTEGER NOT NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS anuncios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  texto TEXT NOT NULL,
  imagem TEXT NOT NULL,
  ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
  ordem INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def configurar(caminho):
    """Define qual arquivo de banco os models vão usar (o app chama ao iniciar)."""
    global _caminho_banco
    _caminho_banco = caminho


@contextmanager
def conectar():
    """Abre uma conexão, entrega para o bloco `with` e fecha no final.

    Se o bloco terminar sem erro, as alterações são gravadas (commit).
    Se der erro no meio, nada é gravado (rollback). Uso:

        with conectar() as con:
            con.execute("UPDATE ...")
    """
    con = sqlite3.connect(_caminho_banco)
    con.row_factory = sqlite3.Row            # linhas acessadas pelo nome da coluna: linha["nome"]
    con.execute("PRAGMA foreign_keys = ON")  # o SQLite só confere as chaves estrangeiras com isto
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def criar_tabelas():
    """Cria as tabelas que faltarem e, se o banco estiver vazio, coloca os dados de exemplo."""
    from models.dados_exemplo import popular  # importado aqui para evitar import circular

    with conectar() as con:
        con.executescript(ESQUEMA)
        banco_vazio = con.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0] == 0
        if banco_vazio:
            popular(con)
