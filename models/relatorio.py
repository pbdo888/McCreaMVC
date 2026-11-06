"""Model Relatorio: números e planilha que a central do administrador mostra."""
from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from models.banco import conectar
from models.usuario import Usuario


class Relatorio:
    """Consultas de análise (reciclagem por bairro e por material) e a planilha de usuários.

    Não tem tabela própria: só lê as outras tabelas e resume os dados.
    """

    # Colunas da planilha: (título, largura)
    COLUNAS_PLANILHA = [
        ("ID", 6), ("Nome", 26), ("E-mail", 30), ("Telefone", 16), ("Nascimento", 12), ("Idade", 7),
        ("Sexo", 14), ("Estado civil", 16), ("Moradores", 10), ("CEP", 11), ("Logradouro", 30),
        ("Número", 8), ("Complemento", 14), ("Bairro", 18), ("Cidade", 16), ("UF", 5),
        ("Latitude", 11), ("Longitude", 11), ("Máquina mais próxima", 26), ("Distância (km)", 13),
        ("Saldo de pontos", 14), ("Pontos acumulados", 16), ("Depósitos", 10), ("Aceita ofertas", 13),
        ("Como conheceu", 20), ("Cadastrado em", 18),
    ]

    @staticmethod
    def por_bairro():
        """Por bairro: quantas máquinas, depósitos, itens, pontos e usuários diferentes."""
        with conectar() as con:
            linhas = con.execute("""
                SELECT m.bairro, COUNT(DISTINCT m.id) AS maquinas, COUNT(d.id) AS depositos,
                       COALESCE(SUM(d.quantidade), 0) AS itens, COALESCE(SUM(d.pontos), 0) AS pontos,
                       COUNT(DISTINCT d.usuario_id) AS usuarios
                FROM maquinas m LEFT JOIN depositos d ON d.maquina_id = m.id
                GROUP BY m.bairro ORDER BY itens DESC, m.bairro""").fetchall()
        return [dict(l) for l in linhas]

    @staticmethod
    def por_material():
        """Quantos itens de cada material já foram reciclados (do mais ao menos reciclado)."""
        with conectar() as con:
            linhas = con.execute("SELECT material, SUM(quantidade) AS itens FROM depositos "
                                 "GROUP BY material ORDER BY itens DESC").fetchall()
        return [dict(l) for l in linhas]

    @classmethod
    def planilha_usuarios(cls):
        """Monta a planilha Excel (.xlsx) com todos os usuários e devolve o arquivo em bytes.

        Para cada usuário: dados do cadastro, idade, máquina mais próxima da casa,
        saldo, pontos acumulados e número de depósitos. Contém dados pessoais (LGPD):
        não compartilhe o arquivo.
        """
        planilha = Workbook()
        aba = planilha.active
        aba.title = "Usuários"
        aba.append([titulo for titulo, _ in cls.COLUNAS_PLANILHA])

        for u in Usuario.listar_todos():
            e = u.endereco
            proximas = u.maquinas_proximas(1)
            maquina, distancia = (proximas[0][0].nome, round(proximas[0][1], 2)) if proximas else (None, None)
            aba.append([
                u.id, u.nome, u.email, u.telefone, date.fromisoformat(u.nascimento), u.idade,
                u.sexo, u.estado_civil, u.moradores, e.cep, e.logradouro, e.numero, e.complemento,
                e.bairro, e.cidade, e.uf, e.lat, e.lng, maquina, distancia,
                u.pontos, u.pontos_acumulados(), u.total_depositos(), "Sim" if u.aceita_ofertas else "Não",
                u.como_conheceu, datetime.strptime(u.criado_em, "%Y-%m-%d %H:%M:%S"),
            ])

        cls._formatar(aba)
        arquivo = BytesIO()  # a planilha é montada na memória: nenhum arquivo fica no disco
        planilha.save(arquivo)
        return arquivo.getvalue()

    @classmethod
    def _formatar(cls, aba):
        """Cabeçalho azul em negrito, larguras das colunas, datas no formato brasileiro e filtros."""
        cabecalho = PatternFill("solid", fgColor="1AA3E8")
        for i, (_, largura) in enumerate(cls.COLUNAS_PLANILHA, start=1):
            celula = aba.cell(row=1, column=i)
            celula.font, celula.fill = Font(bold=True, color="FFFFFF"), cabecalho
            celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            aba.column_dimensions[get_column_letter(i)].width = largura
        for linha in aba.iter_rows(min_row=2):
            linha[4].number_format = "DD/MM/YYYY"           # Nascimento
            linha[-1].number_format = "DD/MM/YYYY HH:MM"    # Cadastrado em
        aba.row_dimensions[1].height = 30
        aba.freeze_panes = "C2"                             # cabeçalho e nome sempre visíveis
        aba.auto_filter.ref = aba.dimensions
