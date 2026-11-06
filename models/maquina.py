"""Model Maquina: as máquinas de reciclagem espalhadas pela cidade."""
import math
from dataclasses import dataclass

from models.banco import conectar
from models.validacao import coordenadas, texto


def distancia_km(lat1, lng1, lat2, lng2):
    """Distância em linha reta entre dois pontos, em quilômetros.

    Usa a distância euclidiana d = √(Δlat² + Δlng²). Cada grau vale cerca de
    111,32 km, e a diferença de longitude é encolhida por cos(latitude) para o
    mapa não ficar "esticado". Serve para ordenar as máquinas por proximidade
    (não é a rota pelas ruas).
    """
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = lat2 - lat1
    return 111.32 * math.hypot(x, y)


@dataclass
class Maquina:
    """Uma máquina de reciclagem: onde fica, quanto cabe e quanto já recebeu."""

    id: int | None
    nome: str
    endereco: str
    bairro: str
    lat: float
    lng: float
    capacidade: int = 500
    ocupacao: int = 0
    status: str = "ativa"

    # ---------- consultas ----------
    @classmethod
    def da_linha(cls, linha):
        """Converte uma linha da tabela `maquinas` em um objeto Maquina."""
        return cls(**dict(linha))

    @classmethod
    def listar_ativas(cls):
        """Todas as máquinas em funcionamento, em ordem alfabética."""
        with conectar() as con:
            linhas = con.execute("SELECT * FROM maquinas WHERE status = 'ativa' ORDER BY nome").fetchall()
        return [cls.da_linha(l) for l in linhas]

    @classmethod
    def buscar_por_id(cls, maquina_id):
        """Devolve a máquina com esse id, ou None se não existir."""
        with conectar() as con:
            linha = con.execute("SELECT * FROM maquinas WHERE id = ?", (maquina_id,)).fetchone()
        return cls.da_linha(linha) if linha else None

    @classmethod
    def mais_proximas(cls, lat, lng, quantidade=3):
        """As `quantidade` máquinas ativas mais perto do ponto (lat, lng).

        Devolve uma lista de pares (maquina, distancia_km), da mais próxima para a mais distante.
        """
        pares = [(m, m.distancia_ate(lat, lng)) for m in cls.listar_ativas()]
        pares.sort(key=lambda par: par[1])
        return pares[:quantidade]

    # ---------- regras de negócio ----------
    @classmethod
    def cadastrar(cls, dados):
        """Valida os dados do formulário do admin e grava uma nova máquina no banco."""
        nome = texto(dados, "nome", "o nome da máquina", maximo=80)
        bairro = texto(dados, "bairro", "o bairro", maximo=60)
        endereco = texto(dados, "endereco", "o endereço", obrigatorio=False, maximo=120)
        lat, lng = coordenadas(dados)
        with conectar() as con:
            cursor = con.execute("INSERT INTO maquinas (nome, endereco, bairro, lat, lng) VALUES (?, ?, ?, ?, ?)",
                                 (nome, endereco, bairro, lat, lng))
        return cls(id=cursor.lastrowid, nome=nome, endereco=endereco, bairro=bairro, lat=lat, lng=lng)

    def distancia_ate(self, lat, lng):
        """Distância (km) desta máquina até o ponto (lat, lng)."""
        return distancia_km(lat, lng, self.lat, self.lng)

    def tem_espaco_para(self, quantidade):
        """True se a máquina está ativa e ainda cabe essa quantidade de itens."""
        return self.status == "ativa" and self.ocupacao + quantidade <= self.capacidade

    @property
    def percentual_ocupado(self):
        """Quanto da capacidade já foi usada, de 0 a 100 (para a barrinha de ocupação)."""
        if not self.capacidade:
            return 100
        return round(100 * self.ocupacao / self.capacidade)

    def para_mapa(self):
        """Só os dados que o mapa do navegador precisa para desenhar o pino."""
        return {"nome": self.nome, "lat": self.lat, "lng": self.lng}
