"""Model Endereco: o endereço fixo da casa do usuário."""
import re
from dataclasses import dataclass
from typing import ClassVar

from models.validacao import ErroValidacao, coordenadas, opcao, texto


@dataclass
class Endereco:
    """Endereço da casa do usuário, com a posição (latitude e longitude) no mapa.

    É um "objeto de valor": não tem tabela própria; suas colunas ficam dentro da
    tabela `usuarios`. No diagrama de classes, Usuario *possui* um Endereco
    (composição). A máquina mais próxima é calculada a partir de lat/lng, sem
    usar a localização em tempo real do celular.
    """

    cep: str
    logradouro: str
    numero: str
    complemento: str
    bairro: str
    cidade: str
    uf: str
    lat: float
    lng: float

    # Siglas aceitas no campo "Estado (UF)"
    UFS: ClassVar[list] = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
                           "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

    @classmethod
    def do_formulario(cls, dados):
        """Valida os campos de endereço enviados pelo formulário e devolve um Endereco.

        Lança ErroValidacao se algum campo estiver errado (ex.: CEP sem 8 dígitos).
        """
        cep = re.sub(r"\D", "", str(dados.get("cep") or ""))  # deixa só os números
        if len(cep) != 8:
            raise ErroValidacao("CEP inválido (são 8 dígitos).")
        lat, lng = coordenadas(dados)
        return cls(
            cep=f"{cep[:5]}-{cep[5:]}",
            logradouro=texto(dados, "logradouro", "a rua"),
            numero=texto(dados, "numero", "o número", maximo=10),
            complemento=texto(dados, "complemento", "o complemento", obrigatorio=False, maximo=60),
            bairro=texto(dados, "bairro", "o bairro", maximo=60),
            cidade=texto(dados, "cidade", "a cidade", maximo=60),
            uf=opcao(dados, "uf", "o estado (UF)", cls.UFS),
            lat=lat,
            lng=lng,
        )

    @classmethod
    def da_linha(cls, linha):
        """Monta o Endereco a partir de uma linha da tabela `usuarios`."""
        return cls(cep=linha["cep"], logradouro=linha["logradouro"], numero=linha["numero"],
                   complemento=linha["complemento"] or "", bairro=linha["bairro"], cidade=linha["cidade"],
                   uf=linha["uf"], lat=linha["lat"], lng=linha["lng"])

    def rua_e_numero(self):
        """Primeira linha do endereço: "Rua Augusta, 1200 · Apto 3"."""
        linha = f"{self.logradouro}, {self.numero}"
        return f"{linha} · {self.complemento}" if self.complemento else linha

    def bairro_e_cidade(self):
        """Segunda linha do endereço: "Consolação, São Paulo - SP"."""
        return f"{self.bairro}, {self.cidade} - {self.uf}"
