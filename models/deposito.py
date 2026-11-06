"""Model Deposito: cada vez que alguém coloca embalagens numa máquina."""
from dataclasses import dataclass
from typing import ClassVar

from models.banco import conectar
from models.usuario import Usuario
from models.validacao import ErroValidacao, inteiro, opcao


@dataclass
class Deposito:
    """Registro de um depósito: quem reciclou, em qual máquina, o quê e quantos pontos ganhou.

    No projeto completo, a própria máquina (sensor infravermelho + visão
    computacional) avisaria o servidor. Aqui o administrador simula o depósito.
    """

    id: int | None
    usuario_id: int
    maquina_id: int
    material: str
    quantidade: int
    pontos: int

    # Pontos ganhos por item de cada material
    PONTOS_POR_MATERIAL: ClassVar[dict] = {"pet": 10, "lata": 15, "vidro": 20, "papel": 5}

    @classmethod
    def registrar(cls, dados):
        """Credita um depósito na máquina mais próxima da casa do usuário.

        Passos: valida usuário, material e quantidade; acha a máquina mais
        próxima; confere se cabe; e então, numa única transação, aumenta a
        ocupação da máquina, soma os pontos no saldo do usuário e grava o
        depósito. Devolve o par (deposito, maquina).
        """
        try:
            usuario = Usuario.buscar_por_id(int(dados.get("usuario_id")))
        except (TypeError, ValueError):
            usuario = None
        if not usuario:
            raise ErroValidacao("Escolha o usuário que fez o depósito.")
        material = opcao(dados, "material", "o material", list(cls.PONTOS_POR_MATERIAL))
        quantidade = inteiro(dados, "quantidade", "a quantidade de itens", minimo=1, maximo=500)

        proximas = usuario.maquinas_proximas(1)
        if not proximas:
            raise ErroValidacao("Não há nenhuma máquina ativa para receber o depósito.")
        maquina, _distancia = proximas[0]
        if not maquina.tem_espaco_para(quantidade):
            raise ErroValidacao(f"A máquina {maquina.nome} está cheia: chame a coleta antes de depositar.")

        pontos = quantidade * cls.PONTOS_POR_MATERIAL[material]
        with conectar() as con:  # tudo ou nada: se um passo falhar, nenhum é gravado
            atualizou = con.execute(
                "UPDATE maquinas SET ocupacao = ocupacao + ? WHERE id = ? AND ocupacao + ? <= capacidade",
                (quantidade, maquina.id, quantidade)).rowcount
            if not atualizou:  # outra pessoa encheu a máquina nesse meio-tempo
                raise ErroValidacao(f"A máquina {maquina.nome} acabou de encher.")
            con.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pontos, usuario.id))
            cursor = con.execute(
                "INSERT INTO depositos (usuario_id, maquina_id, material, quantidade, pontos) VALUES (?, ?, ?, ?, ?)",
                (usuario.id, maquina.id, material, quantidade, pontos))
        maquina.ocupacao += quantidade
        deposito = cls(id=cursor.lastrowid, usuario_id=usuario.id, maquina_id=maquina.id,
                       material=material, quantidade=quantidade, pontos=pontos)
        return deposito, maquina
