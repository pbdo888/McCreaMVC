"""
Preparação dos testes (fixtures do pytest).

Cada teste recebe um app novo, com banco e pasta de uploads TEMPORÁRIOS: o
banco de verdade (mccrea_mvc.db) nunca é tocado. O banco de teste já vem com
os dados de exemplo (ana@exemplo.com / mccrea etc.).
"""
import struct
import zlib

import pytest

from app import criar_app
from config import Config

TOKEN_TESTE = "token-de-teste"


@pytest.fixture
def app(tmp_path):
    """App Flask configurado para teste, com banco novo numa pasta temporária."""

    class ConfigTeste(Config):
        """Configuração de teste: troca banco, uploads, token e chave da sessão."""
        TESTING = True
        BANCO = str(tmp_path / "teste.db")
        PASTA_UPLOADS = str(tmp_path / "uploads")
        ADMIN_TOKEN = TOKEN_TESTE
        SECRET_KEY = "chave-de-teste"

    return criar_app(ConfigTeste)


@pytest.fixture
def cliente(app):
    """Navegador de mentira: faz requisições ao app sem abrir servidor."""
    return app.test_client()


@pytest.fixture
def cliente_logado(cliente):
    """Navegador já logado como a usuária de exemplo Ana Souza."""
    cliente.post("/perfil/entrar", data={"email": "ana@exemplo.com", "senha": "mccrea"})
    return cliente


@pytest.fixture
def cliente_admin(cliente):
    """Navegador já no modo administrador."""
    cliente.post("/admin/entrar", data={"token": TOKEN_TESTE})
    return cliente


def dados_cadastro(**trocas):
    """Formulário de cadastro válido; `trocas` muda só os campos que o teste quer testar."""
    dados = {
        "nome": "Joana Teste", "email": "joana@teste.com", "senha": "segredo1", "senha2": "segredo1",
        "nascimento": "2000-05-10", "telefone": "11912345678", "sexo": "Feminino",
        "estado_civil": "Solteiro(a)", "moradores": "3", "como_conheceu": "Redes sociais",
        "cep": "01310100", "logradouro": "Avenida Paulista", "numero": "1000", "complemento": "",
        "bairro": "Bela Vista", "cidade": "São Paulo", "uf": "SP", "lat": "-23.5650", "lng": "-46.6520",
        "aceite_termos": "1",
    }
    dados.update(trocas)
    return dados


def png_minimo():
    """Bytes de uma imagem PNG de 1x1 pixel (para testar o envio de cartazes)."""
    def bloco(tipo, conteudo):
        """Um "chunk" do formato PNG: tamanho + tipo + conteúdo + verificação (CRC)."""
        return struct.pack(">I", len(conteudo)) + tipo + conteudo + struct.pack(">I", zlib.crc32(tipo + conteudo))
    cabecalho = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(b"\x00\x2f\xb2\x4c")) + bloco(b"IEND", b""))
