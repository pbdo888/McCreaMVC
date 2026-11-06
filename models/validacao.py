"""
Regras de validação compartilhadas pelos models.

Quando um dado não passa numa regra, o model lança ErroValidacao com uma mensagem
pronta para o usuário. O controller captura o erro e mostra a mensagem na view.
"""


class ErroValidacao(ValueError):
    """Erro de regra de negócio (dado inválido). A mensagem é exibida na tela."""


def texto(dados, campo, nome, obrigatorio=True, maximo=120):
    """Lê um campo de texto do formulário, tira os espaços das pontas e confere o tamanho.

    `nome` é como o campo aparece na mensagem de erro (ex.: "o nome completo").
    """
    valor = str(dados.get(campo) or "").strip()
    if obrigatorio and not valor:
        raise ErroValidacao(f"Informe {nome}.")
    if len(valor) > maximo:
        raise ErroValidacao(f"O campo {nome} está muito longo (máximo {maximo} caracteres).")
    return valor


def opcao(dados, campo, nome, opcoes):
    """Confere se o valor escolhido está na lista de opções permitidas (ex.: um <select>)."""
    valor = str(dados.get(campo) or "").strip()
    if valor not in opcoes:
        raise ErroValidacao(f"Escolha {nome}.")
    return valor


def inteiro(dados, campo, nome, minimo, maximo):
    """Converte o campo para número inteiro e confere se está entre `minimo` e `maximo`."""
    try:
        valor = int(dados.get(campo))
    except (TypeError, ValueError):
        raise ErroValidacao(f"Informe {nome} (número inteiro).")
    if not minimo <= valor <= maximo:
        raise ErroValidacao(f"{nome[0].upper() + nome[1:]} deve ficar entre {minimo} e {maximo}.")
    return valor


def coordenadas(dados):
    """Lê latitude e longitude do formulário e confere se são válidas no globo.

    Aceita vírgula ou ponto como separador decimal ("-23,55" ou "-23.55").
    """
    try:
        lat = float(str(dados.get("lat")).replace(",", "."))
        lng = float(str(dados.get("lng")).replace(",", "."))
    except ValueError:
        raise ErroValidacao("Marque o local no mapa (ou digite latitude e longitude).")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ErroValidacao("Coordenadas inválidas.")
    return lat, lng
