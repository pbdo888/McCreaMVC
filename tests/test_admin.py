"""
Testes da aba ADMIN pelas rotas (controller + view), como um navegador faria.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import io

from conftest import png_minimo


def test_central_exige_token(cliente):
    """Sem o token, a central manda para o formulário do token."""
    resposta = cliente.get("/admin/")
    assert resposta.status_code == 302 and "/admin/entrar" in resposta.headers["Location"]


def test_token_errado_nao_entra(cliente):
    """Token errado responde 401 e não abre a central."""
    resposta = cliente.post("/admin/entrar", data={"token": "chute"})
    assert resposta.status_code == 401
    assert cliente.get("/admin/").status_code == 302


def test_token_certo_abre_a_central(cliente_admin):
    """Com o token certo aparecem todos os cartões da central."""
    # Act
    resposta = cliente_admin.get("/admin/")
    # Assert
    assert resposta.status_code == 200
    for cartao in ["Planilha de usuários", "Simular depósito", "Novo cupom", "Nova máquina",
                   "Itens por material", "Novo anúncio", "Anúncios cadastrados (13)", "Reciclagem por bairro"]:
        assert cartao in resposta.text


def test_sair_do_modo_admin(cliente_admin):
    """Depois de sair, a central volta a pedir o token."""
    cliente_admin.post("/admin/sair")
    assert cliente_admin.get("/admin/").status_code == 302


def test_novo_cupom_vira_nova_fase(cliente_admin):
    """O cupom cadastrado aparece na lista de cupons ativos."""
    # Act
    resposta = cliente_admin.post("/admin/cupons", data={"formulario": "cupom", "marca": "Sorveteria Gelo",
                                                         "descricao": "Casquinha grátis", "custo": "50"},
                                  follow_redirects=True)
    # Assert
    assert "Cupom Sorveteria Gelo adicionado" in resposta.text
    assert "7 cupons ativos" in resposta.text


def test_nova_maquina_sem_local_volta_com_o_que_foi_digitado(cliente_admin):
    """Sem marcar o local no mapa, dá erro e o nome digitado continua no campo."""
    # Act
    resposta = cliente_admin.post("/admin/maquinas", data={"formulario": "maquina", "nome": "EcoPonto Butantã",
                                                           "bairro": "Butantã", "lat": "", "lng": ""})
    # Assert
    assert resposta.status_code == 400
    assert "Marque o local no mapa" in resposta.text
    assert 'value="EcoPonto Butantã"' in resposta.text


def test_nova_maquina_entra_no_mapa_e_na_tabela(cliente_admin):
    """A máquina nova conta no total de máquinas e aparece na tabela por bairro."""
    # Act
    resposta = cliente_admin.post("/admin/maquinas", data={"formulario": "maquina", "nome": "EcoPonto Butantã",
                                                           "bairro": "Butantã", "lat": "-23,5710", "lng": "-46,7080"},
                                  follow_redirects=True)
    # Assert
    assert "Máquina EcoPonto Butantã adicionada!" in resposta.text
    assert "as 11 máquinas ativas" in resposta.text
    assert "<td>Butantã</td>" in resposta.text


def test_deposito_pela_central(cliente_admin):
    """Simular depósito mostra os pontos ganhos e o nome da máquina usada."""
    resposta = cliente_admin.post("/admin/depositos", data={"formulario": "deposito", "usuario_id": "1",
                                                            "material": "pet", "quantidade": "3"},
                                  follow_redirects=True)
    assert "+30 pontos para Ana Souza na máquina EcoPonto Paulista." in resposta.text


def test_anuncio_criar_editar_e_excluir_pela_central(cliente_admin):
    """CRUD de anúncio pelas rotas: cria com cartaz, edita o título e exclui."""
    # Create
    resposta = cliente_admin.post("/admin/anuncios", data={
        "formulario": "anuncio", "titulo": "Mutirão de reciclagem", "texto": "Sábado na praça.", "ordem": "0",
        "ativo": "1", "imagem": (io.BytesIO(png_minimo()), "cartaz.png")}, follow_redirects=True)
    assert "Anúncio publicado!" in resposta.text
    assert "Anúncios cadastrados (14)" in resposta.text
    # a imagem enviada só abre no modo admin
    imagem = resposta.text.split('src="/admin/uploads/')[1].split('"')[0]
    assert cliente_admin.get(f"/admin/uploads/{imagem}").status_code == 200
    # Update
    novo_id = resposta.text.split("/admin/anuncios/")[1].split("/")[0]
    resposta = cliente_admin.post(f"/admin/anuncios/{novo_id}/editar", data={
        "titulo": "Mutirão de reciclagem no sábado", "texto": "Sábado na praça.", "ordem": "0", "ativo": "1"},
        follow_redirects=True)
    assert "Mutirão de reciclagem no sábado" in resposta.text
    # Delete
    resposta = cliente_admin.post(f"/admin/anuncios/{novo_id}/excluir", follow_redirects=True)
    assert "Anúncios cadastrados (13)" in resposta.text


def test_imagem_enviada_nao_abre_sem_token(cliente):
    """Fora do modo admin, a rota de uploads manda para o formulário do token."""
    assert cliente.get("/admin/uploads/qualquer.png").status_code == 302


def test_planilha_baixa_um_xlsx(cliente_admin):
    """O botão da planilha devolve um arquivo Excel para download."""
    resposta = cliente_admin.get("/admin/planilha")
    assert resposta.status_code == 200
    assert "spreadsheetml" in resposta.headers["Content-Type"]
    assert "usuarios_mccrea.xlsx" in resposta.headers["Content-Disposition"]
    assert resposta.data[:2] == b"PK"  # todo .xlsx é um arquivo zip por dentro
