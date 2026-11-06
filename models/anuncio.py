"""Model Anuncio: os cartazes de notícias que o administrador publica."""
import os
import uuid
from dataclasses import dataclass
from typing import ClassVar

from models.banco import conectar
from models.validacao import ErroValidacao, inteiro, texto


@dataclass
class Anuncio:
    """Cartaz com título e texto. No projeto completo, os publicados aparecem no
    carrossel de Notícias; aqui o administrador cria, edita, oculta e exclui
    (o CRUD completo: Create, Read, Update, Delete).
    """

    id: int | None
    titulo: str
    texto: str
    imagem: str                 # endereço público da imagem (/static/cartazes/... ou /admin/uploads/...)
    ativo: bool = True          # True = publicado; False = oculto
    ordem: int = 0              # menor aparece antes
    criado_em: str | None = None
    atualizado_em: str | None = None

    # Onde os cartazes enviados são gravados (o app.py troca pelo valor do Config)
    pasta_imagens: ClassVar[str] = os.path.join("uploads", "anuncios")
    # Começo do endereço público desses cartazes (rota definida no admin_controller)
    URL_UPLOADS: ClassVar[str] = "/admin/uploads/"
    MAX_IMAGEM_MB: ClassVar[int] = 5

    # ---------- consultas ----------
    @classmethod
    def da_linha(cls, linha):
        """Converte uma linha da tabela `anuncios` em um objeto Anuncio."""
        dados = dict(linha)
        dados["ativo"] = bool(dados["ativo"])
        return cls(**dados)

    @classmethod
    def listar_todos(cls):
        """Todos os anúncios (publicados e ocultos), na ordem do carrossel."""
        with conectar() as con:
            linhas = con.execute("SELECT * FROM anuncios ORDER BY ordem, id DESC").fetchall()
        return [cls.da_linha(l) for l in linhas]

    @classmethod
    def buscar_por_id(cls, anuncio_id):
        """Devolve o anúncio com esse id, ou None se não existir."""
        with conectar() as con:
            linha = con.execute("SELECT * FROM anuncios WHERE id = ?", (anuncio_id,)).fetchone()
        return cls.da_linha(linha) if linha else None

    # ---------- CRUD ----------
    @classmethod
    def criar(cls, dados, imagem):
        """Cria um anúncio novo. `imagem` são os bytes do arquivo enviado (obrigatório)."""
        campos = cls._validar(dados)
        if not imagem:
            raise ErroValidacao("Escolha a imagem do cartaz.")
        campos["imagem"] = cls._salvar_imagem(imagem)
        with conectar() as con:
            cursor = con.execute(
                "INSERT INTO anuncios (titulo, texto, ordem, ativo, imagem) VALUES (?, ?, ?, ?, ?)",
                (campos["titulo"], campos["texto"], campos["ordem"], int(campos["ativo"]), campos["imagem"]))
        return cls.buscar_por_id(cursor.lastrowid)

    def atualizar(self, dados, imagem=None):
        """Edita título, texto, ordem e publicação. Sem imagem nova, mantém o cartaz atual."""
        campos = self._validar(dados)
        imagem_antiga = self.imagem
        if imagem:
            self.imagem = self._salvar_imagem(imagem)
        self.titulo, self.texto, self.ordem, self.ativo = campos["titulo"], campos["texto"], campos["ordem"], campos["ativo"]
        self._gravar()
        if imagem:
            self._apagar_imagem(imagem_antiga)

    def alternar_publicacao(self):
        """Publica um anúncio oculto ou oculta um publicado."""
        self.ativo = not self.ativo
        self._gravar()

    def excluir(self):
        """Apaga o anúncio do banco e o arquivo do cartaz (se foi enviado pelo admin)."""
        with conectar() as con:
            con.execute("DELETE FROM anuncios WHERE id = ?", (self.id,))
        self._apagar_imagem(self.imagem)

    # ---------- métodos auxiliares (privados) ----------
    def _gravar(self):
        """Salva no banco os valores atuais deste objeto (UPDATE)."""
        with conectar() as con:
            con.execute(
                "UPDATE anuncios SET titulo = ?, texto = ?, ordem = ?, ativo = ?, imagem = ?, "
                "atualizado_em = datetime('now', 'localtime') WHERE id = ?",
                (self.titulo, self.texto, self.ordem, int(self.ativo), self.imagem, self.id))

    @staticmethod
    def _validar(dados):
        """Confere os campos de texto do formulário e devolve um dicionário com eles."""
        titulo = texto(dados, "titulo", "o título", maximo=120)
        if len(titulo) < 3:
            raise ErroValidacao("O título precisa ter pelo menos 3 caracteres.")
        return {
            "titulo": titulo,
            "texto": texto(dados, "texto", "o texto do anúncio", maximo=5000),
            "ordem": inteiro(dados, "ordem", "a ordem", minimo=0, maximo=9999) if dados.get("ordem") else 0,
            "ativo": bool(dados.get("ativo")),
        }

    @staticmethod
    def tipo_da_imagem(conteudo):
        """Descobre o formato pelo começo do arquivo ("assinatura"), sem confiar no nome.

        Devolve "png", "jpg", "gif" ou "webp"; None para qualquer outro (SVG fica de
        fora porque pode conter código JavaScript).
        """
        if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if conteudo.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if conteudo[:6] in (b"GIF87a", b"GIF89a"):
            return "gif"
        if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
            return "webp"
        return None

    @classmethod
    def _salvar_imagem(cls, conteudo):
        """Confere tamanho e formato, grava o arquivo com nome aleatório e devolve o endereço público."""
        if len(conteudo) > cls.MAX_IMAGEM_MB * 1024 * 1024:
            raise ErroValidacao(f"Imagem muito grande (máximo {cls.MAX_IMAGEM_MB} MB).")
        extensao = cls.tipo_da_imagem(conteudo)
        if not extensao:
            raise ErroValidacao("Formato de imagem inválido (use PNG, JPG, WebP ou GIF).")
        nome = f"{uuid.uuid4().hex}.{extensao}"
        os.makedirs(cls.pasta_imagens, exist_ok=True)
        with open(os.path.join(cls.pasta_imagens, nome), "wb") as arquivo:
            arquivo.write(conteudo)
        return cls.URL_UPLOADS + nome

    @classmethod
    def _apagar_imagem(cls, url):
        """Apaga do disco um cartaz enviado pelo admin. Os cartazes iniciais (em static/) ficam."""
        if url and url.startswith(cls.URL_UPLOADS):
            try:
                os.remove(os.path.join(cls.pasta_imagens, os.path.basename(url)))
            except OSError:
                pass
