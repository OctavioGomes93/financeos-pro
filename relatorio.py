"""
relatorio.py — Relatório Mensal Financeiro em PDF
Uso: python relatorio.py           (mês atual)
     python relatorio.py 2026 3    (março/2026)
"""

import os
import sys
import gspread
import pandas as pd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

# ══════════════════════════════════════════
# PALETA DE CORES
# ══════════════════════════════════════════
AZUL        = colors.HexColor("#0d1525")
AZUL_MED    = colors.HexColor("#1a2540")
CIANO       = colors.HexColor("#29d9f5")
VERDE       = colors.HexColor("#22d3a0")
VERMELHO    = colors.HexColor("#f8625a")
AMARELO     = colors.HexColor("#fbbf24")
CINZA       = colors.HexColor("#6b82a8")
CINZA_CLARO = colors.HexColor("#e2e8f0")
BRANCO      = colors.white
PRETO       = colors.HexColor("#0d1525")

MESES_PT = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
            "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

CORES_PIZZA = [
    colors.HexColor("#29d9f5"), colors.HexColor("#8b5cf6"),
    colors.HexColor("#22d3a0"), colors.HexColor("#fbbf24"),
    colors.HexColor("#f8625a"), colors.HexColor("#c084fc"),
    colors.HexColor("#34d399"), colors.HexColor("#fb923c"),
]

# ══════════════════════════════════════════
# CONEXÃO GOOGLE SHEETS
# ══════════════════════════════════════════
def conectar():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.path.join(os.getcwd(), "credenciais.json"), scope
    )
    client   = gspread.authorize(creds)
    planilha = client.open("Controle de Despesas")
    return planilha.sheet1

def carregar_dados(mes, ano):
    ws   = conectar()
    rows = ws.get_all_records()
    df   = pd.DataFrame(rows)
    if df.empty:
        return df

    # Padroniza colunas
    df.columns = df.columns.str.strip()
    mapa = {"data":"Data","descricao":"Descrição","descrição":"Descrição",
            "valor":"Valor","tipo":"Tipo","pessoa":"Pessoa","categoria":"Categoria"}
    df.rename(columns=lambda x: mapa.get(x.lower(), x), inplace=True)

    # Converte valor
    def conv(v):
        try:
            s = str(v).strip().replace("R$","").replace(" ","")
            if "," in s and "." in s: s = s.replace(".","").replace(",",".")
            elif "," in s: s = s.replace(",",".")
            return float(s)
        except: return 0.0

    df["Valor"] = df["Valor"].apply(conv)
    df["_dt"]   = pd.to_datetime(df["Data"], errors="coerce")
    df = df[df["_dt"].dt.month == mes]
    df = df[df["_dt"].dt.year  == ano]
    return df

# ══════════════════════════════════════════
# COMPONENTES VISUAIS
# ══════════════════════════════════════════
def kpi_card(label, valor, cor=CIANO, largura=120, altura=60):
    """Retorna um Drawing com card de KPI."""
    d = Drawing(largura, altura)
    # Fundo
    d.add(Rect(0, 0, largura, altura, rx=6, ry=6,
               fillColor=AZUL_MED, strokeColor=cor, strokeWidth=1))
    # Barra superior colorida
    d.add(Rect(0, altura-4, largura, 4, rx=2, ry=2,
               fillColor=cor, strokeColor=None))
    # Label
    d.add(String(largura/2, altura-18, label,
                 fontName="Helvetica", fontSize=7,
                 fillColor=colors.HexColor("#6b82a8"),
                 textAnchor="middle"))
    # Valor
    d.add(String(largura/2, altura/2-8, valor,
                 fontName="Helvetica-Bold", fontSize=13,
                 fillColor=BRANCO, textAnchor="middle"))
    return d

def grafico_pizza(df_saida):
    """Gráfico de pizza por categoria."""
    if df_saida.empty:
        return None
    top = df_saida.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).head(8)
    if top.empty:
        return None

    d   = Drawing(220, 180)
    pie = Pie()
    pie.x          = 20
    pie.y          = 20
    pie.width      = 130
    pie.height     = 130
    pie.data       = list(top.values)
    pie.labels     = [f"{k[:16]}" for k in top.index]
    pie.simpleLabels = False
    pie.sideLabels   = True
    pie.slices.strokeWidth  = 0.5
    pie.slices.strokeColor  = AZUL

    for i, cor in enumerate(CORES_PIZZA[:len(top)]):
        pie.slices[i].fillColor = cor

    d.add(pie)
    return d

def grafico_barras_mensal(valores_entrada, valores_saida, labels):
    """Gráfico de barras duplas receita vs despesa."""
    if not labels:
        return None

    d    = Drawing(380, 160)
    bc   = VerticalBarChart()
    bc.x = 30
    bc.y = 20
    bc.width  = 340
    bc.height = 120
    bc.data   = [valores_entrada, valores_saida]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.angle  = 30
    bc.categoryAxis.labels.fontSize = 7
    bc.valueAxis.labels.fontSize    = 7
    bc.groupSpacing = 8
    bc.bars[0].fillColor = VERDE
    bc.bars[1].fillColor = VERMELHO
    bc.bars[0].strokeColor = None
    bc.bars[1].strokeColor = None
    bc.valueAxis.strokeColor   = CINZA
    bc.categoryAxis.strokeColor= CINZA

    d.add(bc)
    return d

def tabela_top_categorias(df_saida, n=10):
    """Tabela das top categorias de despesa."""
    if df_saida.empty:
        return None

    top = df_saida.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).head(n)
    total = top.sum()

    dados = [["Categoria", "Valor (R$)", "% do Total"]]
    for cat, val in top.items():
        pct = val / total * 100 if total > 0 else 0
        dados.append([cat, f"R$ {val:,.2f}", f"{pct:.1f}%"])

    t = Table(dados, colWidths=[9*cm, 4*cm, 3*cm])
    t.setStyle(TableStyle([
        # Cabeçalho
        ("BACKGROUND",   (0,0), (-1,0),  AZUL_MED),
        ("TEXTCOLOR",    (0,0), (-1,0),  CIANO),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0),  8),
        ("ALIGN",        (0,0), (-1,0),  "CENTER"),
        ("TOPPADDING",   (0,0), (-1,0),  6),
        ("BOTTOMPADDING",(0,0), (-1,0),  6),
        # Linhas
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,1), (-1,-1), 8),
        ("TEXTCOLOR",    (0,1), (-1,-1), PRETO),
        ("ALIGN",        (1,1), (-1,-1), "RIGHT"),
        ("ALIGN",        (0,1), (0,-1),  "LEFT"),
        ("TOPPADDING",   (0,1), (-1,-1), 4),
        ("BOTTOMPADDING",(0,1), (-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BRANCO, CINZA_CLARO]),
        ("GRID",         (0,0), (-1,-1), 0.3, CINZA),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [4,4,4,4]),
    ]))
    return t

def tabela_lancamentos(df, n=30):
    """Tabela dos últimos lançamentos."""
    if df.empty:
        return None

    df_s = df.sort_values("_dt", ascending=False).head(n)
    dados = [["Data", "Descrição", "Categoria", "Pessoa", "Valor", "Tipo"]]
    for _, r in df_s.iterrows():
        dados.append([
            str(r.get("Data",""))[:10],
            str(r.get("Descrição",""))[:30],
            str(r.get("Categoria",""))[:20],
            str(r.get("Pessoa","")),
            f"R$ {float(r.get('Valor',0)):,.2f}",
            str(r.get("Tipo",""))
        ])

    t = Table(dados, colWidths=[2.2*cm, 5.5*cm, 3.5*cm, 2*cm, 2.5*cm, 1.8*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  AZUL_MED),
        ("TEXTCOLOR",     (0,0), (-1,0),  CIANO),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 7),
        ("ALIGN",         (4,0), (4,-1),  "RIGHT"),
        ("ALIGN",         (0,0), (3,-1),  "LEFT"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BRANCO, CINZA_CLARO]),
        ("GRID",          (0,0), (-1,-1), 0.3, CINZA),
    ]))
    return t

# ══════════════════════════════════════════
# GERAÇÃO DO PDF
# ══════════════════════════════════════════
def gerar_relatorio(mes=None, ano=None):
    hoje  = datetime.today()
    mes   = mes  or hoje.month
    ano   = ano  or hoje.year
    nome_mes = MESES_PT[mes-1]

    print(f"📊 Carregando dados de {nome_mes}/{ano}...")
    df = carregar_dados(mes, ano)

    receita = df[df["Tipo"]=="Entrada"]["Valor"].sum() if not df.empty else 0
    despesa = df[df["Tipo"]=="Saída"]["Valor"].sum()   if not df.empty else 0
    saldo   = receita - despesa
    pct     = (despesa/receita*100) if receita > 0 else 0
    df_saida= df[df["Tipo"]=="Saída"] if not df.empty else pd.DataFrame()

    # Receita por pessoa
    rec_oct = df[(df["Tipo"]=="Entrada")&(df["Pessoa"]=="Octavio")]["Valor"].sum() if not df.empty else 0
    rec_isa = df[(df["Tipo"]=="Entrada")&(df["Pessoa"]=="Isabela")]["Valor"].sum() if not df.empty else 0

    nome_arquivo = f"Relatorio_Financeiro_{nome_mes}_{ano}.pdf"
    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm,   bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── CABEÇALHO ──
    estilo_titulo = ParagraphStyle(
        "titulo", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=22,
        textColor=PRETO, spaceAfter=2
    )
    estilo_sub = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=CINZA, spaceAfter=4
    )
    estilo_secao = ParagraphStyle(
        "secao", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=PRETO, spaceBefore=14, spaceAfter=6,
        borderPad=4
    )
    estilo_nota = ParagraphStyle(
        "nota", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7,
        textColor=CINZA
    )

    story.append(Paragraph(f"Relatorio Financeiro", estilo_titulo))
    story.append(Paragraph(f"{nome_mes} de {ano}  |  Familia Gomes", estilo_sub))
    story.append(Paragraph(f"Gerado em {hoje.strftime('%d/%m/%Y as %H:%M')}", estilo_nota))
    story.append(HRFlowable(width="100%", thickness=1, color=CIANO, spaceAfter=12))

    # ── KPIs ──
    story.append(Paragraph("Resumo do Mes", estilo_secao))
    kpis = Table([[
        kpi_card("RECEITA TOTAL",   f"R$ {receita:,.2f}", VERDE,    130, 65),
        kpi_card("DESPESA TOTAL",   f"R$ {despesa:,.2f}", VERMELHO, 130, 65),
        kpi_card("SALDO LIQUIDO",   f"R$ {saldo:,.2f}",
                 VERDE if saldo>=0 else VERMELHO,           130, 65),
        kpi_card("COMPROMETIDO",    f"{pct:.0f}%",         AMARELO, 130, 65),
    ]], colWidths=[135]*4)
    kpis.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                               ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(kpis)
    story.append(Spacer(1, 6))

    # KPIs por pessoa
    kpis2 = Table([[
        kpi_card("OCTAVIO",  f"R$ {rec_oct:,.2f}", CIANO,   265, 50),
        kpi_card("ISABELA",  f"R$ {rec_isa:,.2f}", CIANO,   265, 50),
    ]], colWidths=[270]*2)
    kpis2.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
    story.append(kpis2)
    story.append(Spacer(1, 12))

    # ── GRÁFICOS LADO A LADO ──
    story.append(Paragraph("Analise de Despesas", estilo_secao))
    pizza = grafico_pizza(df_saida)

    if pizza:
        graf_table = Table([[pizza]], colWidths=[18*cm])
        graf_table.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
        story.append(graf_table)
    story.append(Spacer(1, 8))

    # ── TOP CATEGORIAS ──
    story.append(Paragraph("Top Categorias de Despesa", estilo_secao))
    tab_cat = tabela_top_categorias(df_saida)
    if tab_cat:
        story.append(tab_cat)
    else:
        story.append(Paragraph("Nenhuma despesa registrada neste mes.", estilo_nota))
    story.append(Spacer(1, 12))

    # ── LANÇAMENTOS ──
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA, spaceAfter=8))
    story.append(Paragraph(f"Lancamentos do Mes ({len(df)} registros)", estilo_secao))
    tab_lanc = tabela_lancamentos(df)
    if tab_lanc:
        story.append(tab_lanc)
    else:
        story.append(Paragraph("Nenhum lancamento encontrado.", estilo_nota))

    # ── RODAPÉ ──
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA))
    story.append(Paragraph(
        f"FinanceOS Pro  |  Relatorio de {nome_mes}/{ano}  |  Gerado automaticamente",
        estilo_nota
    ))

    # ── BUILD ──
    doc.build(story)
    print(f"✅ Relatorio gerado: {nome_arquivo}")
    return nome_arquivo

# ══════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) == 3:
        ano_arg = int(sys.argv[1])
        mes_arg = int(sys.argv[2])
        gerar_relatorio(mes_arg, ano_arg)
    else:
        gerar_relatorio()