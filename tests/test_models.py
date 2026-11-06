"""
Testes dos MODELS (regras de negócio), sem passar pelas páginas.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import os
from io import BytesIO

import pytest
from openpyxl import load_workbook

from conftest import dados_cadastro, png_minimo
from models.anuncio import Anuncio
from models.banco import conectar
from models.deposito import Deposito
from models.endereco import Endereco
from models.maquina import Maquina, distancia_km
from models.relatorio import Relatorio
from models.usuario import Usuario
from models.validacao import ErroValidacao


def test_distancia_de_um_grau_de_latitude_e_cerca_de_111_km():
    """1 grau de latitude vale cerca de 111,32 km."""
    # Act
    km = distancia_km(0, 0, 1, 0)
    # Assert
    assert km == pytest.approx(111.32)


def test_endereco_recusa_cep_sem_8_digitos(app):
    """O CEP precisa ter 8 dígitos."""
    with pytest.raises(ErroValidacao, match="CEP"):
        Endereco.do_formulario(dados_cadastro(cep="1234"))


def test_endereco_aceita_virgula_nas_coordenadas(app):
    """Latitude digitada com vírgula (jeito brasileiro) também vale."""
    # Act
    endereco = Endereco.do_formulario(dados_cadastro(lat="-23,5650", lng="-46,6520", cep="01310100"))
    # Assert
    assert endereco.lat == -23.565 and endereco.cep == "01310-100"


def test_cadastrar_guarda_hash_e_nao_a_senha(app):
    """A senha nunca vai para o banco: só o hash, que confere com a senha original."""
    # Act
    usuario = Usuario.cadastrar(dados_cadastro())
    # Assert
    salvo = Usuario.buscar_por_email("joana@teste.com")
    assert salvo.id == usuario.id
    assert salvo.senha_hash != "segredo1"
    assert salvo.verificar_senha("segredo1")
    assert salvo.telefone == "(11) 91234-5678"


def test_cadastrar_recusa_menor_de_13_anos(app):
    """Regra de idade mínima do cadastro."""
    with pytest.raises(ErroValidacao, match="13 anos"):
        Usuario.cadastrar(dados_cadastro(nascimento="2020-01-01"))


def test_cadastrar_recusa_email_repetido(app):
    """Dois cadastros não podem usar o mesmo e-mail (nem com maiúsculas diferentes)."""
    with pytest.raises(ErroValidacao, match="já tem cadastro"):
        Usuario.cadastrar(dados_cadastro(email="ANA@exemplo.com"))


def test_cadastrar_exige_aceite_dos_termos(app):
    """Sem aceitar os termos (LGPD), a conta não é criada."""
    with pytest.raises(ErroValidacao, match="termos"):
        Usuario.cadastrar(dados_cadastro(aceite_termos=""))


def test_autenticar_com_senha_errada_devolve_none(app):
    """Senha errada não entra."""
    assert Usuario.autenticar("ana@exemplo.com", "errada") is None
    assert Usuario.autenticar("ana@exemplo.com", "mccrea").nome == "Ana Souza"


def test_maquinas_proximas_vem_da_mais_perto_para_a_mais_longe(app):
    """A lista de máquinas próximas é ordenada pela distância até a casa."""
    # Arrange
    ana = Usuario.buscar_por_email("ana@exemplo.com")
    # Act
    proximas = ana.maquinas_proximas(3)
    # Assert
    distancias = [km for _, km in proximas]
    assert len(proximas) == 3
    assert distancias == sorted(distancias)
    assert proximas[0][0].nome == "EcoPonto Paulista"


def test_dados_do_mapa_trazem_casa_maquinas_e_a_mais_proxima(app):
    """O mapa do painel recebe a casa, todas as máquinas ativas e a máquina mais perto da casa."""
    # Arrange
    ana = Usuario.buscar_por_email("ana@exemplo.com")
    # Act
    mapa = ana.dados_do_mapa()
    # Assert
    assert mapa["casa"] == {"nome": "Sua casa", "lat": ana.endereco.lat, "lng": ana.endereco.lng}
    assert len(mapa["maquinas"]) == len(Maquina.listar_ativas()) == 10
    assert mapa["proxima"]["nome"] == "EcoPonto Paulista"
    assert mapa["proxima"]["km"] == round(ana.maquinas_proximas(1)[0][1], 2)
    assert {"nome", "lat", "lng"} <= mapa["proxima"].keys()


def test_dados_do_mapa_sem_maquina_ativa_nao_tem_linha(app):
    """Sem nenhuma máquina ativa não existe "mais próxima": o mapa mostra só a casa."""
    # Arrange
    ana = Usuario.buscar_por_email("ana@exemplo.com")
    with conectar() as con:
        con.execute("UPDATE maquinas SET status = 'inativa'")
    # Act
    mapa = ana.dados_do_mapa()
    # Assert
    assert mapa["maquinas"] == []
    assert mapa["proxima"] is None


def test_deposito_credita_pontos_na_maquina_mais_proxima(app):
    """5 latas valem 75 pontos e entram na máquina mais perto da casa."""
    # Arrange
    ana = Usuario.buscar_por_email("ana@exemplo.com")
    maquina_antes = ana.maquinas_proximas(1)[0][0]
    # Act
    deposito, maquina = Deposito.registrar({"usuario_id": ana.id, "material": "lata", "quantidade": "5"})
    # Assert
    assert deposito.pontos == 75
    assert maquina.id == maquina_antes.id
    assert Usuario.buscar_por_id(ana.id).pontos == ana.pontos + 75
    assert Maquina.buscar_por_id(maquina.id).ocupacao == maquina_antes.ocupacao + 5


def test_deposito_recusa_maquina_cheia(app):
    """Máquina sem espaço não recebe depósito e ninguém ganha ponto."""
    # Arrange
    ana = Usuario.buscar_por_email("ana@exemplo.com")
    maquina = ana.maquinas_proximas(1)[0][0]
    with conectar() as con:
        con.execute("UPDATE maquinas SET ocupacao = capacidade WHERE id = ?", (maquina.id,))
    # Act / Assert
    with pytest.raises(ErroValidacao, match="cheia"):
        Deposito.registrar({"usuario_id": ana.id, "material": "pet", "quantidade": "1"})
    assert Usuario.buscar_por_id(ana.id).pontos == ana.pontos


def test_fases_sao_liberadas_pelos_pontos_acumulados(app):
    """Usuário novo começa sem fases; 10 vidros (200 pontos) liberam o cupom de 100."""
    # Arrange
    joana = Usuario.cadastrar(dados_cadastro())
    assert not any(liberada for _, liberada in joana.fases())
    # Act
    Deposito.registrar({"usuario_id": joana.id, "material": "vidro", "quantidade": "10"})
    # Assert
    liberadas = [cupom.custo for cupom, liberada in joana.fases() if liberada]
    assert liberadas == [100]


def test_anuncio_recusa_arquivo_que_nao_e_imagem(app):
    """Um arquivo de texto com nome .png não passa: o formato é conferido pelo conteúdo."""
    with pytest.raises(ErroValidacao, match="Formato"):
        Anuncio.criar({"titulo": "Teste", "texto": "Olá", "ativo": "1"}, b"isto nao e uma imagem")


def test_anuncio_crud_completo(app):
    """Criar, editar, ocultar e excluir um anúncio (o arquivo do cartaz some no final)."""
    # Create
    anuncio = Anuncio.criar({"titulo": "Nova máquina", "texto": "Chegou!", "ordem": "1", "ativo": "1"}, png_minimo())
    arquivo = os.path.join(Anuncio.pasta_imagens, os.path.basename(anuncio.imagem))
    assert os.path.exists(arquivo) and anuncio.ativo
    # Update
    anuncio.atualizar({"titulo": "Nova máquina na Lapa", "texto": "Chegou!", "ordem": "2", "ativo": "1"})
    assert Anuncio.buscar_por_id(anuncio.id).titulo == "Nova máquina na Lapa"
    anuncio.alternar_publicacao()
    assert not Anuncio.buscar_por_id(anuncio.id).ativo
    # Delete
    anuncio.excluir()
    assert Anuncio.buscar_por_id(anuncio.id) is None
    assert not os.path.exists(arquivo)


def test_planilha_tem_uma_linha_por_usuario(app):
    """A planilha traz o cabeçalho e os 8 usuários de exemplo."""
    # Act
    planilha = load_workbook(BytesIO(Relatorio.planilha_usuarios()))
    # Assert
    aba = planilha["Usuários"]
    assert aba.max_row == 1 + 8
    assert aba["B1"].value == "Nome"
    assert {aba.cell(row=i, column=2).value for i in range(2, 10)} >= {"Ana Souza", "Hugo Pires"}


def test_relatorio_por_bairro_soma_os_150_depositos(app):
    """A tabela por bairro tem um total de depósitos igual ao do banco de exemplo."""
    assert sum(b["depositos"] for b in Relatorio.por_bairro()) == 150
