"""
Controller da aba ADMIN (central do administrador).

Rotas (todas, menos "entrar", exigem o token do administrador):
    GET/POST  /admin/entrar                     formulário do token
    POST      /admin/sair                       sair do modo administrador
    GET       /admin/                           central com todos os cartões
    GET       /admin/planilha                   baixar a planilha de usuários (.xlsx)
    POST      /admin/depositos                  simular um depósito numa máquina
    POST      /admin/cupons                     cadastrar cupom (nova fase)
    POST      /admin/maquinas                   cadastrar máquina
    POST      /admin/anuncios                   criar anúncio
    GET/POST  /admin/anuncios/<id>/editar       editar anúncio
    POST      /admin/anuncios/<id>/alternar     publicar / ocultar anúncio
    POST      /admin/anuncios/<id>/excluir      excluir anúncio
    GET       /admin/uploads/<arquivo>          imagem de um cartaz enviado
"""
from io import BytesIO

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request, send_file,
                   send_from_directory, session, url_for)

from controllers.autenticacao import admin_logado, admin_obrigatorio, token_admin_valido
from models.anuncio import Anuncio
from models.cupom import Cupom
from models.deposito import Deposito
from models.maquina import Maquina
from models.relatorio import Relatorio
from models.usuario import Usuario
from models.validacao import ErroValidacao

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------- funções auxiliares do controller ----------
def _mostrar_central(valores=None, status=200):
    """Junta, pelos models, tudo o que a view da central precisa e renderiza a página.

    `valores` traz o que o admin já tinha digitado quando um formulário volta com erro.
    """
    por_material = Relatorio.por_material()
    maquinas = Maquina.listar_ativas()
    pagina = render_template(
        "admin/painel.html",
        valores=valores or {},
        usuarios=Usuario.listar_todos(),
        materiais=Deposito.PONTOS_POR_MATERIAL,
        cupons=Cupom.listar_ativos(),
        maquinas_mapa=[m.para_mapa() for m in maquinas],
        total_maquinas=len(maquinas),
        por_material=por_material,
        maior_material=max([m["itens"] for m in por_material] or [1]),
        por_bairro=Relatorio.por_bairro(),
        anuncios=Anuncio.listar_todos(),
        max_mb=Anuncio.MAX_IMAGEM_MB,
    )
    return pagina, status


def _imagem_enviada():
    """Bytes do arquivo escolhido no campo "imagem" do formulário, ou None se nenhum foi escolhido."""
    arquivo = request.files.get("imagem")
    if not arquivo or not arquivo.filename:
        return None
    return arquivo.read()


def _anuncio_ou_404(anuncio_id):
    """Busca o anúncio pelo id; se não existir, responde "404 - não encontrado"."""
    anuncio = Anuncio.buscar_por_id(anuncio_id)
    if not anuncio:
        abort(404)
    return anuncio


# ---------- entrar e sair ----------
@admin_bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    """GET mostra o formulário do token; POST confere o token e abre a central."""
    if admin_logado():
        return redirect(url_for("admin.painel"))
    if request.method == "POST":
        if token_admin_valido(request.form.get("token")):
            session["admin"] = True
            flash("Modo administrador ativado.", "ok")
            return redirect(url_for("admin.painel"))
        flash("Token de administrador inválido.", "erro")
        return render_template("admin/entrar.html"), 401
    return render_template("admin/entrar.html")


@admin_bp.post("/sair")
def sair():
    """Encerra o modo administrador (o login de usuário, se houver, continua)."""
    session.pop("admin", None)
    flash("Modo administrador encerrado.", "ok")
    return redirect(url_for("perfil.painel"))


# ---------- central ----------
@admin_bp.get("/")
@admin_obrigatorio
def painel():
    """Central do administrador: formulários, análises e lista de anúncios."""
    return _mostrar_central()


@admin_bp.get("/planilha")
@admin_obrigatorio
def baixar_planilha():
    """Gera a planilha de usuários na hora e envia como download."""
    conteudo = Relatorio.planilha_usuarios()
    response = send_file(BytesIO(conteudo), as_attachment=True, download_name="usuarios_mccrea.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Cache-Control"] = "no-store"  # dados pessoais: o navegador não guarda cópia
    return response


@admin_bp.post("/depositos")
@admin_obrigatorio
def registrar_deposito():
    """Simula a máquina: credita os pontos ao usuário na máquina mais próxima da casa dele."""
    try:
        deposito, maquina = Deposito.registrar(request.form)
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return _mostrar_central(request.form, 400)
    usuario = Usuario.buscar_por_id(deposito.usuario_id)
    flash(f"+{deposito.pontos} pontos para {usuario.nome} na máquina {maquina.nome}.", "ok")
    return redirect(url_for("admin.painel", _anchor="deposito"))


@admin_bp.post("/cupons")
@admin_obrigatorio
def criar_cupom():
    """Cadastra um cupom de marca parceira (vira uma nova fase para os usuários)."""
    try:
        cupom = Cupom.cadastrar(request.form)
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return _mostrar_central(request.form, 400)
    flash(f"Cupom {cupom.marca} adicionado como nova fase!", "ok")
    return redirect(url_for("admin.painel", _anchor="cupons"))


@admin_bp.post("/maquinas")
@admin_obrigatorio
def criar_maquina():
    """Cadastra uma máquina no local marcado no mapa."""
    try:
        maquina = Maquina.cadastrar(request.form)
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return _mostrar_central(request.form, 400)
    flash(f"Máquina {maquina.nome} adicionada!", "ok")
    return redirect(url_for("admin.painel", _anchor="maquinas"))


# ---------- anúncios (CRUD) ----------
@admin_bp.post("/anuncios")
@admin_obrigatorio
def criar_anuncio():
    """Cria um anúncio com o cartaz enviado."""
    try:
        Anuncio.criar(request.form, _imagem_enviada())
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return _mostrar_central(request.form, 400)
    flash("Anúncio publicado!" if request.form.get("ativo") else "Anúncio salvo como oculto.", "ok")
    return redirect(url_for("admin.painel", _anchor="anuncios"))


@admin_bp.route("/anuncios/<int:anuncio_id>/editar", methods=["GET", "POST"])
@admin_obrigatorio
def editar_anuncio(anuncio_id):
    """GET mostra o formulário de edição já preenchido; POST grava as alterações."""
    anuncio = _anuncio_ou_404(anuncio_id)
    if request.method == "POST":
        try:
            anuncio.atualizar(request.form, _imagem_enviada())
        except ErroValidacao as erro:
            flash(str(erro), "erro")
            return render_template("admin/anuncio_editar.html", anuncio=anuncio, valores=request.form,
                                   max_mb=Anuncio.MAX_IMAGEM_MB), 400
        flash("Anúncio atualizado!", "ok")
        return redirect(url_for("admin.painel", _anchor="anuncios"))
    valores = {"titulo": anuncio.titulo, "texto": anuncio.texto, "ordem": anuncio.ordem,
               "ativo": "1" if anuncio.ativo else ""}
    return render_template("admin/anuncio_editar.html", anuncio=anuncio, valores=valores,
                           max_mb=Anuncio.MAX_IMAGEM_MB)


@admin_bp.post("/anuncios/<int:anuncio_id>/alternar")
@admin_obrigatorio
def alternar_anuncio(anuncio_id):
    """Publica um anúncio oculto ou oculta um publicado."""
    anuncio = _anuncio_ou_404(anuncio_id)
    anuncio.alternar_publicacao()
    flash("Anúncio publicado!" if anuncio.ativo else "Anúncio ocultado.", "ok")
    return redirect(url_for("admin.painel", _anchor="anuncios"))


@admin_bp.post("/anuncios/<int:anuncio_id>/excluir")
@admin_obrigatorio
def excluir_anuncio(anuncio_id):
    """Exclui o anúncio e o arquivo do cartaz."""
    anuncio = _anuncio_ou_404(anuncio_id)
    anuncio.excluir()
    flash(f"Anúncio \"{anuncio.titulo}\" excluído.", "ok")
    return redirect(url_for("admin.painel", _anchor="anuncios"))


@admin_bp.get("/uploads/<path:arquivo>")
@admin_obrigatorio
def imagem_enviada(arquivo):
    """Entrega a imagem de um cartaz enviado pelo admin (só para quem está no modo admin)."""
    return send_from_directory(current_app.config["PASTA_UPLOADS"], arquivo, max_age=3600)
