"""Model Cupom: os descontos das marcas parceiras (cada cupom é uma "fase")."""
from dataclasses import dataclass

from models.banco import conectar
from models.validacao import inteiro, texto


@dataclass
class Cupom:
    """Cupom de desconto de uma marca parceira.

    Os cupons ativos, em ordem de custo, formam as fases do usuário: uma fase é
    liberada quando os pontos acumulados dele chegam ao custo do cupom.
    """

    id: int | None
    marca: str
    descricao: str
    custo: int
    ativo: bool = True

    @classmethod
    def da_linha(cls, linha):
        """Converte uma linha da tabela `cupons` em um objeto Cupom."""
        return cls(id=linha["id"], marca=linha["marca"], descricao=linha["descricao"],
                   custo=linha["custo"], ativo=bool(linha["ativo"]))

    @classmethod
    def listar_ativos(cls):
        """Cupons em vigor, do mais barato para o mais caro (a ordem das fases)."""
        with conectar() as con:
            linhas = con.execute("SELECT * FROM cupons WHERE ativo = 1 ORDER BY custo, id").fetchall()
        return [cls.da_linha(l) for l in linhas]

    @classmethod
    def cadastrar(cls, dados):
        """Valida o formulário do admin e grava um novo cupom (uma nova fase)."""
        marca = texto(dados, "marca", "a marca parceira", maximo=60)
        descricao = texto(dados, "descricao", "a descrição", maximo=120)
        custo = inteiro(dados, "custo", "o custo em pontos", minimo=1, maximo=100_000)
        with conectar() as con:
            cursor = con.execute("INSERT INTO cupons (marca, descricao, custo) VALUES (?, ?, ?)",
                                 (marca, descricao, custo))
        return cls(id=cursor.lastrowid, marca=marca, descricao=descricao, custo=custo)

    def liberado_para(self, pontos_acumulados):
        """True se quem já juntou `pontos_acumulados` pontos tem esta fase liberada."""
        return pontos_acumulados >= self.custo
