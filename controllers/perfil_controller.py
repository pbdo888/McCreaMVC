"""
Controller da aba PERFIL.

Rotas:
    GET       /perfil/           painel do usuário (ou boas-vindas para visitante)
    GET/POST  /perfil/entrar     formulário de login
    GET/POST  /perfil/cadastro   formulário de criar conta
    GET/POST  /perfil/endereco   formulário de alterar o endereço da casa
    POST      /perfil/sair       sair da conta

Padrão usado nos formulários (PRG: Post/Redirect/Get): se deu certo, o
controller redireciona para outra página (assim o F5 não reenvia o formulário);
se deu erro, mostra a mesma view de novo com a mensagem e o que já foi digitado.
"""
from dataclasses import asdict
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from controllers.autenticacao import login_obrigatorio, usuario_logado
from models.endereco import Endereco
from models.usuario import Usuario
from models.validacao import ErroValidacao

perfil_bp = Blueprint("perfil", __name__, url_prefix="/perfil")


def _opcoes_do_cadastro():
    """Listas que a view usa para montar os campos de escolha (<select>) do cadastro."""
    hoje = date.today()
    try:  # data de quem faz 13 anos hoje: o calendário não deixa escolher depois dela
        nascimento_maximo = hoje.replace(year=hoje.year - Usuario.IDADE_MINIMA)
    except ValueError:  # hoje é 29 de fevereiro e o ano de 13 anos atrás não é bissexto
        nascimento_maximo = hoje.replace(year=hoje.year - Usuario.IDADE_MINIMA, day=28)
    return {
        "sexos": Usuario.SEXOS,
        "estados_civis": Usuario.ESTADOS_CIVIS,
        "como_conheceu": Usuario.COMO_CONHECEU,
        "ufs": Endereco.UFS,
        "nascimento_maximo": nascimento_maximo.isoformat(),
    }


@perfil_bp.get("/")
def painel():
    """Mostra o painel do usuário logado; para quem não entrou, a tela de boas-vindas."""
    usuario = usuario_logado()
    if not usuario:
        return render_template("perfil/visitante.html")
    fases = usuario.fases()
    return render_template(
        "perfil/painel.html",
        usuario=usuario,
        fases=fases,
        fases_liberadas=sum(1 for _, liberada in fases if liberada),
        pontos_acumulados=usuario.pontos_acumulados(),
        maquinas=usuario.maquinas_proximas(3),
        mapa=usuario.dados_do_mapa(),  # casa + máquinas + a mais próxima, para o mapa do navegador
    )


@perfil_bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    """GET mostra o formulário de login; POST confere e-mail e senha com o model Usuario."""
    if usuario_logado():  # já entrou: não há por que mostrar o login
        return redirect(url_for("perfil.painel"))
    if request.method == "POST":
        usuario = Usuario.autenticar(request.form.get("email"), request.form.get("senha"))
        if usuario:
            session["usuario_id"] = usuario.id
            flash(f"Olá, {usuario.primeiro_nome}!", "ok")
            return redirect(url_for("perfil.painel"))
        flash("E-mail ou senha incorretos.", "erro")
        return render_template("perfil/entrar.html", email=request.form.get("email", "")), 401
    return render_template("perfil/entrar.html", email="")


@perfil_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    """GET mostra o formulário de criar conta; POST pede ao model para cadastrar."""
    if usuario_logado():  # quem já está na conta precisa sair antes de criar outra
        return redirect(url_for("perfil.painel"))
    if request.method == "POST":
        try:
            usuario = Usuario.cadastrar(request.form)
        except ErroValidacao as erro:
            flash(str(erro), "erro")
            return render_template("perfil/cadastro.html", valores=request.form, **_opcoes_do_cadastro()), 400
        session["usuario_id"] = usuario.id  # quem acabou de se cadastrar já entra na conta
        flash(f"Conta criada! Bem-vindo, {usuario.primeiro_nome}.", "ok")
        return redirect(url_for("perfil.painel"))
    return render_template("perfil/cadastro.html", valores={"moradores": "1"}, **_opcoes_do_cadastro())


@perfil_bp.route("/endereco", methods=["GET", "POST"])
@login_obrigatorio
def alterar_endereco():
    """GET mostra o endereço atual para editar; POST grava o novo endereço."""
    usuario = usuario_logado()
    if request.method == "POST":
        try:
            usuario.alterar_endereco(request.form)
        except ErroValidacao as erro:
            flash(str(erro), "erro")
            return render_template("perfil/endereco.html", valores=request.form, ufs=Endereco.UFS), 400
        flash("Endereço atualizado! As máquinas mais próximas foram recalculadas.", "ok")
        return redirect(url_for("perfil.painel"))
    return render_template("perfil/endereco.html", valores=asdict(usuario.endereco), ufs=Endereco.UFS)


@perfil_bp.post("/sair")
def sair():
    """Tira o usuário da sessão (o modo administrador, se estiver ativo, continua)."""
    session.pop("usuario_id", None)
    flash("Você saiu da sua conta.", "ok")
    return redirect(url_for("perfil.painel"))
