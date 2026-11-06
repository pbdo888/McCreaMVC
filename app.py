"""
McCrea · versão MVC com as abas Perfil e Admin.

Rode com:  python app.py   e abra  http://localhost:5070

Este arquivo só MONTA a aplicação: liga a configuração, o banco (models), as
páginas (views, na pasta views/) e as rotas (controllers). O trabalho de cada
aba fica nos controllers, e as regras de negócio ficam nos models.
"""
from flask import Flask, redirect, render_template, url_for

from config import Config
from controllers.admin_controller import admin_bp
from controllers.autenticacao import admin_logado, usuario_logado
from controllers.perfil_controller import perfil_bp
from models import banco
from models.anuncio import Anuncio


def formatar_data(texto):
    """Filtro das views: "2026-11-02 14:30:00" vira "02/11/2026"."""
    if not texto:
        return ""
    ano, mes, dia = str(texto)[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def formatar_km(valor):
    """Filtro das views: 1.2345 vira "1,23 km" (vírgula decimal, como no Brasil)."""
    return f"{valor:.2f}".replace(".", ",") + " km"


def criar_app(config=Config):
    """Cria e configura a aplicação Flask (padrão "application factory").

    Os testes chamam criar_app() com outra configuração (banco temporário),
    sem mexer no banco de verdade.
    """
    app = Flask(__name__, template_folder="views")  # V de MVC: os templates ficam em views/
    app.config.from_object(config)

    # M de MVC: aponta os models para o banco e a pasta de uploads, e cria as tabelas
    banco.configurar(app.config["BANCO"])
    Anuncio.pasta_imagens = app.config["PASTA_UPLOADS"]
    Anuncio.MAX_IMAGEM_MB = app.config["MAX_IMAGEM_MB"]
    banco.criar_tabelas()

    # C de MVC: cada aba tem o seu controller (Blueprint)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(admin_bp)

    # Filtros usados nos templates: {{ texto|data_br }} e {{ numero|km }}
    app.add_template_filter(formatar_data, "data_br")
    app.add_template_filter(formatar_km, "km")

    @app.context_processor
    def dados_do_topo():
        """Variáveis disponíveis em todas as views (o topo mostra quem está logado)."""
        return {"usuario_atual": usuario_logado(), "modo_admin": admin_logado()}

    @app.get("/")
    def inicio():
        """A página inicial é a aba Perfil."""
        return redirect(url_for("perfil.painel"))

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        """Página amigável para endereços que não existem."""
        return render_template("erro.html", titulo="Página não encontrada",
                               mensagem="O endereço que você abriu não existe."), 404

    @app.errorhandler(413)
    def arquivo_grande(_erro):
        """O Flask recusa envios maiores que MAX_CONTENT_LENGTH antes de chegar ao controller."""
        return render_template("erro.html", titulo="Arquivo muito grande",
                               mensagem=f"O cartaz pode ter no máximo {app.config['MAX_IMAGEM_MB']} MB."), 413

    return app


if __name__ == "__main__":
    aplicacao = criar_app()
    aplicacao.run(debug=True, port=aplicacao.config["PORTA"])
