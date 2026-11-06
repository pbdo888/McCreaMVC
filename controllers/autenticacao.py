"""
Controle de acesso compartilhado pelos controllers.

A sessão do Flask é um cookie assinado com a SECRET_KEY: o navegador guarda,
mas não consegue alterar. Nela ficam só duas informações:
    session["usuario_id"] -> id do usuário que entrou na aba Perfil
    session["admin"]      -> True depois que o token do administrador foi aceito
"""
import secrets
from functools import wraps

from flask import current_app, flash, g, redirect, session, url_for

from models.usuario import Usuario


def usuario_logado():
    """Devolve o Usuario da sessão (ou None). Busca no banco uma vez só por requisição."""
    if "usuario" not in g:
        usuario_id = session.get("usuario_id")
        g.usuario = Usuario.buscar_por_id(usuario_id) if usuario_id else None
        if usuario_id and not g.usuario:  # a conta não existe mais: limpa a sessão
            session.pop("usuario_id", None)
    return g.usuario


def admin_logado():
    """True se o token do administrador já foi conferido nesta sessão."""
    return session.get("admin") is True


def token_admin_valido(token):
    """Compara o token digitado com o ADMIN_TOKEN do .env.

    compare_digest leva o mesmo tempo acertando ou errando, para ninguém
    descobrir o token medindo o tempo de resposta. Sem token no .env, ninguém entra.
    """
    esperado = current_app.config.get("ADMIN_TOKEN", "")
    return bool(esperado) and secrets.compare_digest(str(token or "").encode(), esperado.encode())


def login_obrigatorio(rota):
    """Decorador: só deixa abrir a rota quem entrou na conta; os outros vão para "Entrar"."""
    @wraps(rota)
    def protegida(*args, **kwargs):
        """Roda antes da rota: sem login, redireciona; com login, executa a rota original."""
        if not usuario_logado():
            flash("Entre na sua conta para continuar.", "erro")
            return redirect(url_for("perfil.entrar"))
        return rota(*args, **kwargs)
    return protegida


def admin_obrigatorio(rota):
    """Decorador: só deixa abrir a rota quem informou o token do administrador."""
    @wraps(rota)
    def protegida(*args, **kwargs):
        """Roda antes da rota: sem o token, redireciona; com o token, executa a rota original."""
        if not admin_logado():
            flash("Informe o token de administrador para abrir a central.", "erro")
            return redirect(url_for("admin.entrar"))
        return rota(*args, **kwargs)
    return protegida
