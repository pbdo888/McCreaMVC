"""
M de MVC: os MODELS.

Cada classe representa uma "coisa" do sistema (uma tabela do banco ou um
conceito do negócio) e guarda as regras dela: o que é um cadastro válido, como
achar a máquina mais próxima, quantos pontos vale um depósito etc.

Os models não sabem nada de páginas HTML nem do Flask: recebem dados, aplicam
as regras, conversam com o banco (models/banco.py) e devolvem objetos.

    Usuario   ── possui um ──> Endereco
    Usuario   ── faz vários ──> Deposito ── em uma ──> Maquina
    Cupom     (fases liberadas pelos pontos acumulados do Usuario)
    Anuncio   (cartazes publicados pelo administrador)
    Relatorio (resumos e planilha a partir das outras tabelas)
"""
