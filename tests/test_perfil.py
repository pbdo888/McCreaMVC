"""
Testes da aba PERFIL pelas rotas (controller + view), como um navegador faria.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import json
import re

from conftest import dados_cadastro


def test_visitante_ve_boas_vindas(cliente):
    """Quem não entrou vê o convite para criar conta."""
    # Act
    resposta = cliente.get("/perfil/")
    # Assert
    assert resposta.status_code == 200
    assert "Bem-vindo ao McCrea" in resposta.text


def test_raiz_redireciona_para_o_perfil(cliente):
    """A página inicial (/) leva para a aba Perfil."""
    resposta = cliente.get("/")
    assert resposta.status_code == 302 and resposta.headers["Location"].endswith("/perfil/")


def test_login_certo_mostra_o_painel(cliente):
    """E-mail e senha certos abrem o painel com nome, pontos e máquinas próximas."""
    # Act
    resposta = cliente.post("/perfil/entrar", data={"email": "ana@exemplo.com", "senha": "mccrea"},
                            follow_redirects=True)
    # Assert
    assert "Ana Souza" in resposta.text
    assert "Máquinas perto de casa" in resposta.text
    assert "EcoPonto Paulista" in resposta.text
    assert "fases liberadas" in resposta.text


def test_login_errado_continua_no_formulario(cliente):
    """Senha errada responde 401 e mantém o e-mail digitado."""
    resposta = cliente.post("/perfil/entrar", data={"email": "ana@exemplo.com", "senha": "errada"})
    assert resposta.status_code == 401
    assert "E-mail ou senha incorretos" in resposta.text
    assert 'value="ana@exemplo.com"' in resposta.text


def test_cadastro_completo_ja_entra_na_conta(cliente):
    """Depois de criar a conta, o painel já mostra o novo usuário."""
    # Act
    resposta = cliente.post("/perfil/cadastro", data=dados_cadastro(), follow_redirects=True)
    # Assert
    assert "Conta criada! Bem-vindo, Joana." in resposta.text
    assert "Joana Teste" in resposta.text
    assert "Avenida Paulista, 1000" in resposta.text


def test_cadastro_com_erro_mantem_o_que_foi_digitado(cliente):
    """Com erro, o formulário volta preenchido (menos as senhas) e mostra a mensagem."""
    # Act
    resposta = cliente.post("/perfil/cadastro", data=dados_cadastro(telefone="123"))
    # Assert
    assert resposta.status_code == 400
    assert "Telefone inválido" in resposta.text
    assert 'value="Joana Teste"' in resposta.text
    assert "segredo1" not in resposta.text


def test_painel_tem_o_mapa_da_casa_ate_a_maquina_mais_proxima(cliente_logado):
    """O painel manda ao navegador os dados do mapa (casa, máquinas e a mais próxima) e carrega o script."""
    # Act
    resposta = cliente_logado.get("/perfil/")
    # Assert: o JSON que o JavaScript vai ler está no atributo data-mapa-casa
    dados = json.loads(re.search(r"data-mapa-casa='([^']*)'", resposta.text).group(1))
    assert dados["casa"]["nome"] == "Sua casa"
    assert dados["proxima"]["nome"] == "EcoPonto Paulista"
    assert len(dados["maquinas"]) == 10
    assert "js/mapa_perfil.js" in resposta.text
    assert "Mais próxima: <b>EcoPonto Paulista</b>" in resposta.text


def test_alterar_endereco_exige_login(cliente):
    """Sem login, a tela de endereço manda para "Entrar"."""
    resposta = cliente.get("/perfil/endereco")
    assert resposta.status_code == 302 and "/perfil/entrar" in resposta.headers["Location"]


def test_alterar_endereco_atualiza_o_painel(cliente_logado):
    """Novo endereço aparece no painel e muda a máquina mais próxima."""
    # Arrange: a casa vai para perto da máquina de Santana
    novo = dados_cadastro(cep="02031000", logradouro="Rua Voluntários da Pátria", numero="2000",
                          bairro="Santana", lat="-23.5030", lng="-46.6280")
    # Act
    resposta = cliente_logado.post("/perfil/endereco", data=novo, follow_redirects=True)
    # Assert
    assert "Endereço atualizado" in resposta.text
    assert "Rua Voluntários da Pátria, 2000" in resposta.text
    primeira_maquina = resposta.text.split("tile destaque")[1].split("</b>")[0]
    assert "EcoPonto Santana" in primeira_maquina


def test_quem_ja_entrou_nao_ve_login_nem_cadastro(cliente_logado):
    """Logado, as telas de entrar e de criar conta levam direto ao painel."""
    for rota in ["/perfil/entrar", "/perfil/cadastro"]:
        resposta = cliente_logado.get(rota)
        assert resposta.status_code == 302 and resposta.headers["Location"].endswith("/perfil/")


def test_sair_volta_para_boas_vindas(cliente_logado):
    """Depois de sair, a aba Perfil volta a ser a de visitante."""
    resposta = cliente_logado.post("/perfil/sair", follow_redirects=True)
    assert "Você saiu da sua conta." in resposta.text
    assert "Bem-vindo ao McCrea" in resposta.text
