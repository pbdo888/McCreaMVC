"""
Configurações do projeto.

Os valores secretos (token do administrador e chave da sessão) ficam no arquivo
.env, que não vai para o Git. Os caminhos são montados a partir da pasta do
projeto, então o app funciona mesmo se for iniciado de outra pasta.
"""
import os
import secrets

from dotenv import load_dotenv

# Pasta onde este arquivo está (a raiz do projeto)
PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))

# Lê o arquivo .env (se existir) e coloca os valores nas variáveis de ambiente
load_dotenv(os.path.join(PASTA_PROJETO, ".env"))


class Config:
    """Agrupa todas as configurações usadas pelo Flask e pelos models.

    O Flask lê os atributos em MAIÚSCULAS desta classe com
    app.config.from_object(Config). Nos testes, uma subclasse troca o banco e a
    pasta de uploads por arquivos temporários.
    """

    # Assina o cookie da sessão (login). Sem ela no .env, cada reinício desloga todo mundo.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

    # Token que abre a central do administrador (definido no .env)
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

    # Arquivo do banco de dados SQLite (criado sozinho na primeira execução)
    BANCO = os.path.join(PASTA_PROJETO, "mccrea_mvc.db")

    # Pasta onde ficam os cartazes enviados pelo administrador
    PASTA_UPLOADS = os.path.join(PASTA_PROJETO, "uploads", "anuncios")

    # Tamanho máximo do cartaz e de toda a requisição (cartaz + campos de texto)
    MAX_IMAGEM_MB = 5
    MAX_CONTENT_LENGTH = (MAX_IMAGEM_MB + 1) * 1024 * 1024

    # Cookie de sessão protegido: o JavaScript não lê e outros sites não enviam em POST
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Porta do servidor de desenvolvimento (o projeto completo usa a 5050).
    # Evite a 5060 e a 5061: o Chrome e o Firefox bloqueiam (ERR_UNSAFE_PORT).
    PORTA = 5070
