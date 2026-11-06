"""Model Usuario: quem recicla nas máquinas e junta pontos."""
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from werkzeug.security import check_password_hash, generate_password_hash

from models.banco import conectar
from models.cupom import Cupom
from models.endereco import Endereco
from models.maquina import Maquina
from models.validacao import ErroValidacao, inteiro, opcao, texto


@dataclass
class Usuario:
    """Pessoa cadastrada no McCrea.

    Guarda os dados do cadastro, o endereço fixo da casa (um Endereco) e o saldo
    de pontos. A senha nunca é guardada: só o "hash" dela (uma impressão digital
    que não pode ser desfeita).
    """

    id: int | None
    nome: str
    email: str
    senha_hash: str
    nascimento: str            # data no formato AAAA-MM-DD
    sexo: str
    estado_civil: str
    telefone: str
    moradores: int
    como_conheceu: str | None
    aceita_ofertas: bool
    endereco: Endereco
    pontos: int = 0            # saldo atual (sobe a cada depósito)
    criado_em: str | None = None

    # Opções dos campos de escolha do cadastro (a view monta os <select> com estas listas)
    SEXOS: ClassVar[list] = ["Feminino", "Masculino", "Outro", "Prefiro não informar"]
    ESTADOS_CIVIS: ClassVar[list] = ["Solteiro(a)", "Casado(a)", "União estável", "Divorciado(a)", "Viúvo(a)",
                                     "Prefiro não informar"]
    COMO_CONHECEU: ClassVar[list] = ["Redes sociais", "Indicação de amigo", "Vi uma máquina na rua",
                                     "Notícia ou imprensa", "Outro"]
    IDADE_MINIMA: ClassVar[int] = 13
    SENHA_MINIMA: ClassVar[int] = 6

    # ---------- conversão banco <-> objeto ----------
    @classmethod
    def da_linha(cls, linha):
        """Converte uma linha da tabela `usuarios` em um objeto Usuario (com seu Endereco)."""
        return cls(
            id=linha["id"], nome=linha["nome"], email=linha["email"], senha_hash=linha["senha_hash"],
            nascimento=linha["nascimento"], sexo=linha["sexo"], estado_civil=linha["estado_civil"],
            telefone=linha["telefone"], moradores=linha["moradores"], como_conheceu=linha["como_conheceu"],
            aceita_ofertas=bool(linha["aceita_ofertas"]), endereco=Endereco.da_linha(linha),
            pontos=linha["pontos"], criado_em=linha["criado_em"],
        )

    # ---------- consultas ----------
    @classmethod
    def buscar_por_id(cls, usuario_id):
        """Devolve o usuário com esse id, ou None se não existir."""
        with conectar() as con:
            linha = con.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return cls.da_linha(linha) if linha else None

    @classmethod
    def buscar_por_email(cls, email):
        """Devolve o usuário com esse e-mail (sem diferenciar maiúsculas), ou None."""
        with conectar() as con:
            linha = con.execute("SELECT * FROM usuarios WHERE email = ?", (email.strip().lower(),)).fetchone()
        return cls.da_linha(linha) if linha else None

    @classmethod
    def listar_todos(cls):
        """Todos os usuários, em ordem alfabética (usado pela central do administrador)."""
        with conectar() as con:
            linhas = con.execute("SELECT * FROM usuarios ORDER BY nome").fetchall()
        return [cls.da_linha(l) for l in linhas]

    # ---------- casos de uso: cadastrar, entrar, alterar endereço ----------
    @classmethod
    def cadastrar(cls, dados):
        """Valida o formulário de cadastro, grava o novo usuário e devolve o objeto criado.

        Regras: e-mail válido e ainda não usado, senha com 6 ou mais caracteres (e
        confirmada), idade mínima de 13 anos, telefone com DDD, de 1 a 30
        moradores, endereço completo com posição no mapa e aceite dos termos (LGPD).
        """
        email = str(dados.get("email") or "").strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ErroValidacao("E-mail inválido.")
        senha = str(dados.get("senha") or "")
        if len(senha) < cls.SENHA_MINIMA:
            raise ErroValidacao(f"A senha precisa ter pelo menos {cls.SENHA_MINIMA} caracteres.")
        if senha != str(dados.get("senha2") or ""):
            raise ErroValidacao("As senhas não são iguais.")

        usuario = cls(
            id=None,
            nome=texto(dados, "nome", "o nome completo"),
            email=email,
            senha_hash=generate_password_hash(senha),
            nascimento=cls._validar_nascimento(dados.get("nascimento")),
            sexo=opcao(dados, "sexo", "o sexo", cls.SEXOS),
            estado_civil=opcao(dados, "estado_civil", "o estado civil", cls.ESTADOS_CIVIS),
            telefone=cls._validar_telefone(dados.get("telefone")),
            moradores=inteiro(dados, "moradores", "o número de moradores", minimo=1, maximo=30),
            como_conheceu=cls._validar_como_conheceu(dados.get("como_conheceu")),
            aceita_ofertas=bool(dados.get("aceita_ofertas")),
            endereco=Endereco.do_formulario(dados),
        )
        if not dados.get("aceite_termos"):
            raise ErroValidacao("Para criar a conta, aceite os termos de uso e a política de privacidade.")
        if cls.buscar_por_email(email):
            raise ErroValidacao("Este e-mail já tem cadastro. Use Entrar.")
        usuario._inserir()
        return usuario

    @classmethod
    def autenticar(cls, email, senha):
        """Confere e-mail e senha. Devolve o Usuario se estiverem certos, senão None."""
        usuario = cls.buscar_por_email(str(email or ""))
        if usuario and usuario.verificar_senha(str(senha or "")):
            return usuario
        return None

    def verificar_senha(self, senha):
        """True se `senha` corresponde ao hash guardado no banco."""
        return check_password_hash(self.senha_hash, senha)

    def alterar_endereco(self, dados):
        """Valida o novo endereço e grava no banco (a máquina mais próxima muda junto)."""
        novo = Endereco.do_formulario(dados)
        with conectar() as con:
            con.execute(
                "UPDATE usuarios SET cep = ?, logradouro = ?, numero = ?, complemento = ?, bairro = ?, "
                "cidade = ?, uf = ?, lat = ?, lng = ? WHERE id = ?",
                (novo.cep, novo.logradouro, novo.numero, novo.complemento, novo.bairro, novo.cidade,
                 novo.uf, novo.lat, novo.lng, self.id))
        self.endereco = novo

    # ---------- informações do painel de perfil ----------
    @property
    def primeiro_nome(self):
        """Só o primeiro nome, para as saudações ("Olá, Ana!")."""
        return self.nome.split()[0]

    @property
    def idade(self):
        """Idade em anos completos, calculada a partir da data de nascimento."""
        return self._anos_desde(date.fromisoformat(self.nascimento))

    def pontos_acumulados(self):
        """Soma de todos os pontos que o usuário já ganhou (não diminui ao gastar o saldo)."""
        with conectar() as con:
            return con.execute("SELECT COALESCE(SUM(pontos), 0) FROM depositos WHERE usuario_id = ?",
                               (self.id,)).fetchone()[0]

    def total_depositos(self):
        """Quantas vezes o usuário depositou embalagens nas máquinas."""
        with conectar() as con:
            return con.execute("SELECT COUNT(*) FROM depositos WHERE usuario_id = ?", (self.id,)).fetchone()[0]

    def fases(self):
        """Lista de pares (cupom, liberado) com todos os cupons ativos, na ordem das fases."""
        acumulados = self.pontos_acumulados()
        return [(cupom, cupom.liberado_para(acumulados)) for cupom in Cupom.listar_ativos()]

    def maquinas_proximas(self, quantidade=3):
        """As máquinas mais perto da casa do usuário: lista de pares (maquina, distancia_km)."""
        return Maquina.mais_proximas(self.endereco.lat, self.endereco.lng, quantidade)

    def dados_do_mapa(self):
        """O que o mapa do painel precisa para desenhar: a casa, todas as máquinas e a mais próxima.

        Devolve um dicionário simples (vira JSON na view):
            casa     -> {"nome", "lat", "lng"} do endereço fixo do usuário
            maquinas -> pinos de todas as máquinas ativas
            proxima  -> a máquina mais perto da casa (None se não houver máquina ativa);
                        o JavaScript liga a casa até ela com uma linha tracejada
        """
        mais_proxima = self.maquinas_proximas(1)
        return {
            "casa": {"nome": "Sua casa", "lat": self.endereco.lat, "lng": self.endereco.lng},
            "maquinas": [m.para_mapa() for m in Maquina.listar_ativas()],
            "proxima": {**mais_proxima[0][0].para_mapa(), "km": round(mais_proxima[0][1], 2)} if mais_proxima else None,
        }

    # ---------- métodos auxiliares (privados: começam com _) ----------
    def _inserir(self):
        """Grava este usuário (ainda sem id) na tabela `usuarios` e guarda o id gerado."""
        e = self.endereco
        try:
            with conectar() as con:
                cursor = con.execute(
                    "INSERT INTO usuarios (nome, email, senha_hash, nascimento, sexo, estado_civil, telefone, "
                    "moradores, como_conheceu, aceita_ofertas, cep, logradouro, numero, complemento, bairro, "
                    "cidade, uf, lat, lng) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.nome, self.email, self.senha_hash, self.nascimento, self.sexo, self.estado_civil,
                     self.telefone, self.moradores, self.como_conheceu, int(self.aceita_ofertas), e.cep,
                     e.logradouro, e.numero, e.complemento, e.bairro, e.cidade, e.uf, e.lat, e.lng))
        except sqlite3.IntegrityError:  # dois cadastros com o mesmo e-mail ao mesmo tempo
            raise ErroValidacao("Este e-mail já tem cadastro. Use Entrar.")
        self.id = cursor.lastrowid

    @staticmethod
    def _anos_desde(nascimento):
        """Quantos aniversários já se passaram desde a data `nascimento`."""
        hoje = date.today()
        return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))

    @classmethod
    def _validar_nascimento(cls, valor):
        """Confere a data de nascimento e a idade mínima. Devolve a data em AAAA-MM-DD."""
        try:
            nascimento = date.fromisoformat(str(valor))
        except ValueError:
            raise ErroValidacao("Data de nascimento inválida.")
        anos = cls._anos_desde(nascimento)
        if anos < cls.IDADE_MINIMA or anos > 120:
            raise ErroValidacao(f"É preciso ter pelo menos {cls.IDADE_MINIMA} anos para se cadastrar.")
        return nascimento.isoformat()

    @staticmethod
    def _validar_telefone(valor):
        """Confere o telefone (DDD + número, 10 ou 11 dígitos) e formata como (11) 91234-5678."""
        digitos = re.sub(r"\D", "", str(valor or ""))
        if len(digitos) not in (10, 11):
            raise ErroValidacao("Telefone inválido (DDD + número).")
        return f"({digitos[:2]}) {digitos[2:-4]}-{digitos[-4:]}"

    @classmethod
    def _validar_como_conheceu(cls, valor):
        """Campo opcional: vazio vira None; se preenchido, precisa ser uma das opções."""
        valor = str(valor or "").strip()
        if valor and valor not in cls.COMO_CONHECEU:
            raise ErroValidacao("Opção inválida em 'Como nos conheceu?'.")
        return valor or None
