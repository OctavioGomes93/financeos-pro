import os
import io
import re
import time
import json
import hashlib
import calendar
import tempfile
import streamlit as st
import os
port = int(os.environ.get("PORT", 8080))
import pandas as pd
import gspread
import pdfplumber
from ofxparse import OfxParser
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from rapidfuzz import process, fuzz
from datetime import datetime, date, timedelta

# ── Voz: usa st.audio_input nativo (Streamlit 1.46+) ──
# Não precisa de pacote externo — funciona direto no browser e celular
AUDIO_OK = hasattr(st, "audio_input")

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

# ══════════════════════════════════════════
# CONFIG PAGE
# ══════════════════════════════════════════
st.set_page_config(layout="wide", page_title="FinanceOS Pro", page_icon="💼", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap');
:root {
    --bg:#0d1525; --surface:#151e30; --card:#1a2540; --card-hover:#1f2d4d;
    --border:#2a3a5c; --border-light:#344870;
    --accent:#29d9f5; --accent-dim:rgba(41,217,245,.12);
    --accent2:#8b5cf6; --accent2-dim:rgba(139,92,246,.12);
    --green:#22d3a0; --green-dim:rgba(34,211,160,.12);
    --red:#f8625a; --red-dim:rgba(248,98,90,.12);
    --yellow:#fbbf24; --yellow-dim:rgba(251,191,36,.12);
    --orange:#fb923c; --orange-dim:rgba(251,146,60,.12);
    --text:#f0f4ff; --text-sec:#b8c5e0; --muted:#6b82a8;
    --radius:14px; --radius-sm:9px;
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background-color:var(--bg)!important;color:var(--text)!important;}
.hero{background:linear-gradient(135deg,#111f3f 0%,#0d1525 55%,#131e38 100%);border:1px solid var(--border);border-radius:20px;padding:2.2rem 2.8rem;margin-bottom:1.8rem;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:320px;height:320px;background:radial-gradient(circle,rgba(41,217,245,.14) 0%,transparent 70%);pointer-events:none;}
.hero::after{content:'';position:absolute;bottom:-100px;left:25%;width:280px;height:280px;background:radial-gradient(circle,rgba(139,92,246,.1) 0%,transparent 70%);pointer-events:none;}
.hero h1{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;background:linear-gradient(90deg,#f0f4ff 0%,var(--accent) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 .35rem;letter-spacing:-1px;}
.hero p{color:var(--muted);font-size:.9rem;margin:0;font-weight:300;}
.hero-badge{display:inline-block;background:rgba(41,217,245,.1);border:1px solid rgba(41,217,245,.3);color:var(--accent);font-size:.68rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:.2rem .7rem;border-radius:100px;margin-bottom:.9rem;}
.kpi-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:1.4rem 1.6rem;position:relative;overflow:hidden;transition:transform .2s,border-color .25s,box-shadow .25s;}
.kpi-card:hover{transform:translateY(-3px);border-color:var(--border-light);box-shadow:0 8px 28px rgba(0,0,0,.25);}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--radius) var(--radius) 0 0;}
.kpi-card.green::before{background:linear-gradient(90deg,var(--green),#34d399);}
.kpi-card.red::before{background:linear-gradient(90deg,var(--red),#fb7185);}
.kpi-card.blue::before{background:linear-gradient(90deg,var(--accent),#818cf8);}
.kpi-card.purple::before{background:linear-gradient(90deg,var(--accent2),#c084fc);}
.kpi-card.yellow::before{background:linear-gradient(90deg,var(--yellow),var(--orange));}
.kpi-icon{font-size:1.4rem;margin-bottom:.5rem;display:block;}
.kpi-label{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin-bottom:.4rem;}
.kpi-value{font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;color:var(--text);line-height:1;}
.kpi-sub{font-size:.76rem;color:var(--text-sec);margin-top:.4rem;}
.alert-card{border-radius:12px;padding:1rem 1.25rem;margin:.5rem 0;border-left:4px solid;display:flex;align-items:flex-start;gap:.75rem;}
.alert-card.warn{background:var(--yellow-dim);border-color:var(--yellow);}
.alert-card.error{background:var(--red-dim);border-color:var(--red);}
.alert-card.ok{background:var(--green-dim);border-color:var(--green);}
.alert-card.info{background:var(--accent-dim);border-color:var(--accent);}
.alert-icon{font-size:1.2rem;margin-top:.05rem;}
.alert-title{font-weight:700;font-size:.88rem;color:var(--text);margin-bottom:.15rem;}
.alert-msg{font-size:.8rem;color:var(--text-sec);}
.section-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--text-sec);letter-spacing:.2px;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
.section-title::after{content:'';flex:1;height:1px;background:var(--border);margin-left:.6rem;}
.stTabs [data-baseweb="tab-list"]{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:12px!important;padding:4px!important;gap:2px!important;flex-wrap:wrap!important;}
.stTabs [data-baseweb="tab"]{border-radius:var(--radius-sm)!important;font-family:'DM Sans',sans-serif!important;font-size:.8rem!important;font-weight:500!important;color:var(--muted)!important;padding:.45rem .9rem!important;transition:all .2s!important;border:none!important;}
.stTabs [aria-selected="true"]{background:var(--card)!important;color:var(--accent)!important;border:1px solid var(--border-light)!important;font-weight:600!important;}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.4rem!important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stSelectbox>div>div,.stDateInput>div>div>input,.stTextArea textarea{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:var(--radius-sm)!important;color:var(--text)!important;font-family:'DM Sans',sans-serif!important;font-size:.88rem!important;transition:border-color .2s,box-shadow .2s!important;}
label,.stSelectbox label,.stTextInput label,.stNumberInput label{font-size:.75rem!important;font-weight:600!important;color:var(--muted)!important;text-transform:uppercase!important;letter-spacing:1px!important;margin-bottom:.25rem!important;}
.stButton>button{background:linear-gradient(135deg,var(--accent) 0%,#0fb8d8 100%)!important;color:#071220!important;font-family:'Syne',sans-serif!important;font-weight:700!important;font-size:.8rem!important;letter-spacing:.4px!important;border:none!important;border-radius:var(--radius-sm)!important;padding:.5rem 1.4rem!important;transition:all .2s!important;box-shadow:0 3px 14px rgba(41,217,245,.22)!important;}
.stButton>button:hover{transform:translateY(-1px)!important;box-shadow:0 6px 22px rgba(41,217,245,.38)!important;}
[data-testid="stForm"]{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.75rem;}
.stDataFrame{border-radius:12px;overflow:hidden;}
[data-testid="stDataFrame"]>div{border:1px solid var(--border)!important;border-radius:12px!important;}
[data-testid="stFileUploader"]{background:var(--card)!important;border:2px dashed var(--border)!important;border-radius:16px!important;padding:1.25rem!important;transition:border-color .2s!important;}
[data-testid="stFileUploader"]:hover{border-color:var(--accent)!important;}
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.1rem 1.4rem;}
[data-testid="stMetricValue"]{font-family:'Syne',sans-serif!important;font-size:1.5rem!important;font-weight:800!important;color:var(--text)!important;}
.ai-card{background:linear-gradient(135deg,rgba(41,217,245,.06) 0%,rgba(139,92,246,.06) 100%);border:1px solid rgba(41,217,245,.22);border-radius:14px;padding:1.1rem 1.4rem;margin:.65rem 0;position:relative;}
.ai-card::before{content:'🤖';position:absolute;top:-10px;left:1rem;background:var(--bg);padding:0 .35rem;font-size:.85rem;}
.ai-desc{font-weight:600;font-size:.92rem;color:var(--text);margin-bottom:.4rem;}
.ai-meta{font-size:.76rem;color:var(--muted);}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:.75rem;}
.cal-day{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.4rem .3rem;text-align:center;font-size:.72rem;min-height:52px;position:relative;}
.cal-day.today{border-color:var(--accent);background:var(--accent-dim);}
.cal-day.has-event{border-color:var(--yellow);}
.cal-num{font-weight:700;font-size:.82rem;color:var(--text-sec);display:block;}
.cal-dot{width:6px;height:6px;border-radius:50%;margin:.15rem auto 0;}
.cal-dot.red{background:var(--red);}.cal-dot.green{background:var(--green);}
.prog-bar{background:var(--border);border-radius:100px;height:7px;overflow:hidden;margin:.4rem 0;}
.prog-fill{height:100%;border-radius:100px;transition:width .6s ease;}
.badge{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase;padding:.18rem .55rem;border-radius:100px;}
.badge.green{background:var(--green-dim);color:var(--green);}.badge.red{background:var(--red-dim);color:var(--red);}
.badge.yellow{background:var(--yellow-dim);color:var(--yellow);}.badge.blue{background:var(--accent-dim);color:var(--accent);}
.badge.purple{background:var(--accent2-dim);color:var(--accent2);}
::-webkit-scrollbar{width:5px;height:5px;}::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border-light);border-radius:10px;}
.element-container{animation:fadeUp .3s ease both;}
@keyframes fadeUp{from{transform:translateY(6px);opacity:0;}to{transform:translateY(0);opacity:1;}}
hr{border-color:var(--border)!important;}
</style>
""", unsafe_allow_html=True)

hoje = datetime.today()
MESES_PT = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
DIAS_PT  = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
data_pt  = f"{DIAS_PT[hoje.weekday()]}, {hoje.day:02d} de {MESES_PT[hoje.month-1]} de {hoje.year}"

st.markdown(f"""
<div class="hero">
    <div class="hero-badge">⚡ Finance OS Pro</div>
    <h1>💼 Sistema Financeiro</h1>
    <p>IA adaptativa · OFX · CSV · Fixos · Parcelas · Patrimônio &nbsp;|&nbsp;
    <b style="color:var(--text-sec);">{data_pt}</b></p>
</div>
""", unsafe_allow_html=True)

# ── Auto-refresh a cada 2 minutos ──
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=120000, key="autorefresh")
except ImportError:
    pass

# ══════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    creds_json = (
            os.environ.get("GOOGLE_CREDENTIALS_JSON") or
            os.environ.get("GOOGLE_CREDENTIALS") or
            ""
    )

    if creds_json:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(creds_json), scope
        )
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(os.getcwd(), "credenciais.json"), scope
        )

    client = gspread.authorize(creds)
    planilha = client.open("Controle de Despesas")

    def gor(nome, cols):
        try:
            return planilha.worksheet(nome)
        except:
            ws = planilha.add_worksheet(title=nome, rows="200", cols="20")
            ws.append_row(cols)
            return ws

    return {
        "lanc": planilha.sheet1,
        "bens": gor("Bens", ["Descrição", "Tipo", "Valor", "Proprietário"]),
        "regras": gor("Regras", ["Descricao", "Categoria"]),
        "fixos": gor("Fixos", ["Descricao", "Categoria", "Valor", "Pessoa", "DiaVencimento"]),
        "parcelas": gor("Parcelas",
                        ["Descricao", "Categoria", "Valor", "TotalParcelas", "ParcelaAtual", "Pessoa", "DataInicio"]),
        "metas": gor("Metas", ["Categoria", "ValorMeta", "Mes", "Ano"]),
    }
ws=conectar()

def preparar(df):
    if df.empty: return df
    df.columns=df.columns.str.strip()
    mapa={"data":"Data","descricao":"Descrição","descrição":"Descrição","valor":"Valor","tipo":"Tipo","pessoa":"Pessoa","categoria":"Categoria"}
    df.rename(columns=lambda x:mapa.get(x.lower(),x),inplace=True)
    for c in ["Data","Pessoa","Categoria","Descrição","Valor","Tipo"]:
        if c not in df.columns: df[c]=""
    return df

def retry_load(worksheet,n=5,wait=12):
    for i in range(n):
        try: return preparar(pd.DataFrame(worksheet.get_all_records()))
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and i<n-1: st.toast(f"⏳ Rate limit — aguardando {wait}s ({i+1}/{n})",icon="⚠️"); time.sleep(wait)
            else: raise
    return preparar(pd.DataFrame())

@st.cache_data(ttl=120,show_spinner=False)
def load_lanc():    return retry_load(ws["lanc"])
@st.cache_data(ttl=300,show_spinner=False)
def load_regras():  return retry_load(ws["regras"])
@st.cache_data(ttl=300,show_spinner=False)
def load_fixos():   return retry_load(ws["fixos"])
@st.cache_data(ttl=300,show_spinner=False)
def load_parcelas():return retry_load(ws["parcelas"])
@st.cache_data(ttl=300,show_spinner=False)
def load_metas():   return retry_load(ws["metas"])
def load(w):        return retry_load(w)

with st.spinner("🔄 Carregando..."):
    df=load_lanc(); regras=load_regras(); fixos=load_fixos()
    parcelas=load_parcelas(); metas=load_metas()
def converter_valor(v):
    """Converte valor em qualquer formato para float."""
    try:
        s = str(v).strip().replace("R$","").replace(" ","")
        if not s or s in ("","None","nan"): return 0.0
        # Formato brasileiro: 1.234,56
        if "," in s and "." in s:
            s = s.replace(".","").replace(",",".")
        # Só vírgula: 1234,56
        elif "," in s:
            s = s.replace(",",".")
        # Já é número normal: 1234.56
        return float(s)
    except:
        return 0.0

df["Valor"] = df["Valor"].apply(converter_valor)

def gerar_id(d,desc,v): return hashlib.md5(f"{d}{desc}{v}".encode()).hexdigest()
df["ID"]  = df.apply(lambda x:gerar_id(str(x["Data"]),str(x["Descrição"]),str(x["Valor"])),axis=1)
df["_row"] = range(2, len(df)+2)  # linha real na planilha

def inserir(lns):
    if lns: ws["lanc"].append_rows(lns); load_lanc.clear()

def salvar_regra(desc,cat):
    ws["regras"].append_row([desc,cat]); load_regras.clear()

def excluir_linha(row_num):
    try:
        ws["lanc"].delete_rows(int(row_num)); load_lanc.clear(); return True
    except Exception as e:
        st.error(f"❌ Erro ao excluir: {e}"); return False

def editar_linha(row_num, data, pessoa, categoria, descricao, valor, tipo):
    try:
        ws["lanc"].update(f"A{row_num}:F{row_num}",
            [[str(data),pessoa,categoria,descricao,float(valor),tipo]])
        load_lanc.clear(); return True
    except Exception as e:
        st.error(f"❌ Erro ao editar: {e}"); return False

def limpar_planilha():
    try:
        ws["lanc"].clear()
        ws["lanc"].append_row(["Data","Pessoa","Categoria","Descrição","Valor","Tipo"])
        load_lanc.clear(); return True
    except Exception as e:
        st.error(f"❌ Erro ao limpar: {e}"); return False

def tabela_com_excluir(df_input, key_prefix="tab"):
    """Tabela com filtros + botões editar e excluir."""
    if df_input.empty:
        st.info("Nenhum lançamento encontrado."); return

    cf1,cf2,cf3 = st.columns(3)
    f_tipo   = cf1.selectbox("Filtrar tipo",   ["Todos","Entrada","Saída"], key=f"{key_prefix}_tipo")
    f_pessoa = cf2.selectbox("Filtrar pessoa", ["Todos"]+pessoas,           key=f"{key_prefix}_pessoa")
    f_busca  = cf3.text_input("🔍 Buscar",                                  key=f"{key_prefix}_busca")

    df_f = df_input.copy()
    if f_tipo   != "Todos": df_f = df_f[df_f["Tipo"]==f_tipo]
    if f_pessoa != "Todos": df_f = df_f[df_f["Pessoa"]==f_pessoa]
    if f_busca:             df_f = df_f[df_f["Descrição"].str.contains(f_busca,case=False,na=False)]
    df_f = df_f.reset_index(drop=True)

    if df_f.empty:
        st.info("Nenhum resultado."); return

    # Cabeçalho
    h1,h2,h3,h4,h5,h6,h7,h8 = st.columns([2,1.5,2,3,1.5,1.5,.55,.55])
    for col,txt in [(h1,"Data"),(h2,"Pessoa"),(h3,"Categoria"),(h4,"Descrição"),(h5,"Valor"),(h6,"Tipo"),(h7,"✏️"),(h8,"🗑️")]:
        col.markdown(f'<div style="font-size:.68rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:1px;">{txt}</div>',unsafe_allow_html=True)
    st.markdown('<hr style="margin:.15rem 0 .35rem;">',unsafe_allow_html=True)

    for idx, row in df_f.iterrows():
        row_num = row.get("_row")
        cor = "#22d3a0" if row.get("Tipo")=="Entrada" else "#f8625a"
        c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([2,1.5,2,3,1.5,1.5,.55,.55])
        c1.markdown(f'<div style="font-size:.78rem;color:var(--text-sec);padding:.2rem 0;">{row.get("Data","")}</div>',unsafe_allow_html=True)
        c2.markdown(f'<div style="font-size:.78rem;padding:.2rem 0;">{row.get("Pessoa","")}</div>',unsafe_allow_html=True)
        c3.markdown(f'<div style="font-size:.74rem;color:var(--muted);padding:.2rem 0;">{row.get("Categoria","")}</div>',unsafe_allow_html=True)
        c4.markdown(f'<div style="font-size:.78rem;padding:.2rem 0;">{row.get("Descrição","")}</div>',unsafe_allow_html=True)
        c5.markdown(f'<div style="font-size:.78rem;font-weight:700;color:{cor};padding:.2rem 0;">R$ {float(row.get("Valor",0)):,.2f}</div>',unsafe_allow_html=True)
        c6.markdown(f'<div style="font-size:.74rem;color:var(--muted);padding:.2rem 0;">{row.get("Tipo","")}</div>',unsafe_allow_html=True)

        if c7.button("✏️", key=f"e_{key_prefix}_{idx}"):
            st.session_state[f"ed_{key_prefix}_{idx}"] = not st.session_state.get(f"ed_{key_prefix}_{idx}",False)
            st.session_state[f"dl_{key_prefix}_{idx}"] = False

        if c8.button("🗑️", key=f"d_{key_prefix}_{idx}"):
            st.session_state[f"dl_{key_prefix}_{idx}"] = not st.session_state.get(f"dl_{key_prefix}_{idx}",False)
            st.session_state[f"ed_{key_prefix}_{idx}"] = False

        # ── Formulário edição ──
        if st.session_state.get(f"ed_{key_prefix}_{idx}"):
            with st.container():
                st.markdown('<div style="background:var(--accent-dim);border:1px solid rgba(41,217,245,.2);border-radius:12px;padding:1rem;margin:.4rem 0;">',unsafe_allow_html=True)
                e1,e2,e3 = st.columns(3)
                with e1:
                    try: dv=datetime.strptime(str(row.get("Data","")),"%Y-%m-%d").date()
                    except: dv=hoje.date()
                    ed=st.date_input("📅 Data",value=dv,key=f"ed_d_{key_prefix}_{idx}")
                    ep=st.selectbox("👤 Pessoa",pessoas,index=pessoas.index(row.get("Pessoa",pessoas[0])) if row.get("Pessoa") in pessoas else 0,key=f"ed_p_{key_prefix}_{idx}")
                with e2:
                    et=st.selectbox("↕️ Tipo",["Saída","Entrada"],index=0 if row.get("Tipo","Saída")=="Saída" else 1,key=f"ed_t_{key_prefix}_{idx}")
                    le=cat_desp if et=="Saída" else cat_rec
                    ca_=row.get("Categoria",""); ic=le.index(ca_) if ca_ in le else 0
                    ec=st.selectbox("🏷️ Categoria",le,index=ic,key=f"ed_c_{key_prefix}_{idx}")
                with e3:
                    edesc=st.text_input("📝 Descrição",value=row.get("Descrição",""),key=f"ed_ds_{key_prefix}_{idx}")
                    ev=st.number_input("💰 Valor",value=float(row.get("Valor",0)),min_value=0.0,format="%.2f",key=f"ed_v_{key_prefix}_{idx}")
                st.markdown('</div>',unsafe_allow_html=True)
                s1,s2=st.columns(2)
                if s1.button("💾 Salvar",key=f"ed_ok_{key_prefix}_{idx}",use_container_width=True):
                    if row_num and editar_linha(row_num,ed,ep,ec,edesc,ev,et):
                        st.success("✅ Atualizado!"); st.session_state[f"ed_{key_prefix}_{idx}"]=False; st.rerun()
                if s2.button("❌ Cancelar",key=f"ed_no_{key_prefix}_{idx}",use_container_width=True):
                    st.session_state[f"ed_{key_prefix}_{idx}"]=False; st.rerun()

        # ── Confirmação exclusão ──
        if st.session_state.get(f"dl_{key_prefix}_{idx}"):
            ca,cb,cc_=st.columns([3,1,1])
            ca.markdown(f'<div style="font-size:.82rem;color:var(--yellow);padding:.3rem 0;">⚠️ Excluir <b>{row.get("Descrição","")}</b> — R$ {float(row.get("Valor",0)):,.2f}?</div>',unsafe_allow_html=True)
            if cb.button("✅ Sim",key=f"dl_ok_{key_prefix}_{idx}"):
                if row_num and excluir_linha(row_num):
                    st.success("✅ Excluído!"); st.session_state[f"dl_{key_prefix}_{idx}"]=False; st.rerun()
                else: st.error("❌ Não encontrado. Atualize a página.")
            if cc_.button("❌ Não",key=f"dl_no_{key_prefix}_{idx}"):
                st.session_state[f"dl_{key_prefix}_{idx}"]=False; st.rerun()

def sugerir(desc):
    if regras.empty or "Descricao" not in regras.columns: return None,None
    lista=regras["Descricao"].tolist(); match=process.extractOne(desc,lista)
    if not match: return None,None
    if match[1]>80: idx=lista.index(match[0]); return regras.iloc[idx]["Categoria"],match[1]
    if match[1]>60: idx=lista.index(match[0]); return None,(regras.iloc[idx]["Categoria"],match[0],match[1])
    return None,None

PARC_RE=re.compile(r'(\d{1,2})[/\-](\d{1,2})|parc(?:ela)?\s*(\d+)',re.IGNORECASE)
def detectar_parcela(desc):
    m=PARC_RE.search(desc)
    if m:
        if m.group(1) and m.group(2): return int(m.group(1)),int(m.group(2))
        if m.group(3): return int(m.group(3)),None
    return None,None

def match_fixo(desc,lista,thr=72):
    if not lista: return None
    nomes=[f.get("Descricao","") for f in lista]
    match=process.extractOne(desc,nomes,scorer=fuzz.partial_ratio)
    if match and match[1]>=thr: return lista[nomes.index(match[0])]
    return None

# ══════════════════════════════════════════
# MOTOR DE CONCILIAÇÃO BANCÁRIA
# ══════════════════════════════════════════
TOLERANCIA_VALOR = 0.10   # R$ 0,10 (IOF, arredondamentos)
TOLERANCIA_DIAS  = 3      # dias de diferença aceitos (compensação bancária)

def conciliar_extrato(transacoes_extrato, df_manuais, fixos_df=None):
    """
    Cruza cada transação do extrato com lançamentos manuais e fixos.
    Status possíveis:
      - 'fixo'       : bate com despesa fixa cadastrada → NÃO importar (já lançado)
      - 'match'      : bate com lançamento manual → mantém nome/categoria manual
      - 'similar'    : valor bate mas descrição difere → pergunta ao usuário
      - 'duplicado'  : já existe lançamento idêntico → ignora
      - 'novo'       : sem correspondência → categorizar
    """
    resultado = []
    df_m = df_manuais.copy()
    df_m["_dt"] = pd.to_datetime(df_m["Data"], errors="coerce")
    df_m["Valor"] = df_m["Valor"].apply(converter_valor)
    usados = set()

    # Monta lista de fixos para detecção
    fixos_lista = []
    if fixos_df is not None and not fixos_df.empty and "Descricao" in fixos_df.columns:
        fixos_lista = fixos_df.to_dict("records")

    for tx in transacoes_extrato:
        desc_ext  = str(tx.get("Descricao",""))
        valor_ext = float(tx.get("Valor", 0))
        data_ext  = pd.to_datetime(tx.get("Data",""), errors="coerce")
        tipo_ext  = tx.get("Tipo","Saída")

        # ── 1. Verifica se é um FIXO cadastrado → bloqueia importação ──
        fixo_encontrado = None
        if tipo_ext == "Saída":
            for f in fixos_lista:
                nome_fixo = str(f.get("Descricao",""))
                score_f   = fuzz.partial_ratio(desc_ext.lower(), nome_fixo.lower())
                if score_f >= 70:
                    fixo_encontrado = f
                    break

        if fixo_encontrado:
            resultado.append({
                **tx,
                "_status":        "fixo",
                "_manual":        None,
                "_score":         100,
                "_fixo_nome":     fixo_encontrado.get("Descricao",""),
                "_fixo_cat":      fixo_encontrado.get("Categoria",""),
                "_nome_manual":   fixo_encontrado.get("Descricao",""),
                "_categoria_manual": fixo_encontrado.get("Categoria",""),
                "_pessoa_manual": fixo_encontrado.get("Pessoa","Octavio"),
            })
            continue

        # ── 2. Verifica duplicata exata ──
        é_duplicado = False
        for idx, man in df_m.iterrows():
            if abs(float(man.get("Valor",0)) - valor_ext) <= 0.01:
                data_man = man["_dt"]
                if not pd.isna(data_man) and not pd.isna(data_ext):
                    if abs((data_ext - data_man).days) == 0:
                        sc = fuzz.ratio(desc_ext.lower(), str(man.get("Descrição","")).lower())
                        if sc >= 85:
                            é_duplicado = True; break

        if é_duplicado:
            resultado.append({**tx, "_status":"duplicado", "_manual":None, "_score":100})
            continue

        # ── 3. Busca match/similar com lançamentos manuais ──
        melhor_idx   = None
        melhor_score = 0
        melhor_tipo  = "novo"

        for idx, man in df_m.iterrows():
            if idx in usados: continue
            if man.get("Tipo","") != tipo_ext: continue

            valor_man = float(man.get("Valor", 0))
            if abs(valor_man - valor_ext) > TOLERANCIA_VALOR: continue

            data_man   = man["_dt"]
            if pd.isna(data_man): continue
            delta_dias = abs((data_ext - data_man).days) if not pd.isna(data_ext) else 99
            if delta_dias > TOLERANCIA_DIAS: continue

            score_desc = fuzz.partial_ratio(
                desc_ext.lower(), str(man.get("Descrição","")).lower()
            )
            score = score_desc + (3 - delta_dias) * 5

            if score > melhor_score:
                melhor_score = score
                melhor_idx   = idx
                melhor_tipo  = "match" if score_desc >= 75 else "similar"

        if melhor_idx is not None:
            man_row = df_m.loc[melhor_idx]
            usados.add(melhor_idx)
            resultado.append({
                **tx,
                "_status":           melhor_tipo,
                "_manual":           man_row.to_dict(),
                "_score":            melhor_score,
                "_nome_manual":      man_row.get("Descrição",""),
                "_categoria_manual": man_row.get("Categoria",""),
                "_pessoa_manual":    man_row.get("Pessoa",""),
            })
        else:
            resultado.append({**tx, "_status":"novo", "_manual":None, "_score":0})

    return resultado

# ══════════════════════════════════════════
# CATEGORIAS BPO
# ══════════════════════════════════════════
GRUPOS={
    "💚 Receitas":["Salário Octavio","Salário Isabela","13º Salário","Férias","Bônus / PLR","Rendimento Investimentos","Receita Extra"],
    "🏠 Moradia":["Aluguel / Financiamento","Condomínio","IPTU","Energia Elétrica","Água e Esgoto","Gás","Internet / TV / Streaming","Faxina / Diarista","Manutenção / Reforma"],
    "🚗 Transporte":["Combustível","Estacionamento","Uber / Táxi / Transporte","IPVA / Licenciamento","Seguro Auto","Manutenção Veículo"],
    "🍽️ Alimentação":["Supermercado / Feira","Padaria / Café","Restaurante / Delivery","Lanche / Fast Food"],
    "❤️ Saúde & Bem-Estar":["Plano de Saúde","Farmácia","Médico / Dentista / Exames","Academia / Gympass","Pet Shop / Veterinário","Psicólogo / Terapia"],
    "👨‍👩‍👧 Família & Educação":["Escola / Creche Otto","Material Escolar","Cursos / Assinaturas Educação","Presentes","Lazer / Passeios Família"],
    "💳 Financeiro & Seguros":["Anuidade Cartão","FIES / Empréstimo","Consórcio","Seguros (Vida/Residencial)","Investimento Mensal","Previdência Privada","Tarifas Bancárias"],
    "🎯 Estilo de Vida":["Roupas / Calçados / Acessórios","Barbearia / Beleza / Estética","Viagens / Hospedagem","Eletrônicos / Tecnologia","Assinaturas Digitais","Outros"],
}
cat_all     =[c for g in GRUPOS.values() for c in g]
cat_desp    =[c for g,cs in GRUPOS.items() if g!="💚 Receitas" for c in cs]
cat_rec     =GRUPOS["💚 Receitas"]
pessoas     =["Octavio","Isabela"]

def opts_ui(despesa=False,receita=False):
    out=[]
    for g,cs in GRUPOS.items():
        if despesa and g=="💚 Receitas": continue
        if receita and g!="💚 Receitas": continue
        out.append(f"── {g} ──"); out.extend(cs)
    return out

def limpa(v): return None if (v and v.startswith("──")) else v

# ══════════════════════════════════════════
# ALERTAS
# ══════════════════════════════════════════
def alertas(df,fixos,parcelas):
    res=[]; ma=hoje.month; ya=hoje.year
    dfc=df.copy(); dfc["_dt"]=pd.to_datetime(dfc["Data"],errors="coerce")
    dm=dfc[(dfc["_dt"].dt.month==ma)&(dfc["_dt"].dt.year==ya)]
    rec=dm[dm["Tipo"]=="Entrada"]["Valor"].sum()
    desp=dm[dm["Tipo"]=="Saída"]["Valor"].sum()
    saldo=rec-desp
    if rec==0: res.append(("error","💸 Sem receita no mês","Nenhuma entrada registrada ainda."))
    if rec>0 and desp/rec>0.9: res.append(("warn","⚠️ Despesa elevada",f"{desp/rec*100:.0f}% da receita comprometida."))
    if saldo<0: res.append(("error","🔴 Saldo negativo",f"Saldo: R$ {saldo:,.2f}"))
    if not fixos.empty and "Descricao" in fixos.columns:
        desc_m=dm["Descrição"].str.lower().tolist()
        for _,f in fixos.iterrows():
            n=str(f.get("Descricao","")).lower()
            if n and not any(n[:10] in d for d in desc_m):
                res.append(("warn",f"📋 Fixo ausente",f'"{f.get("Descricao","")}" não lançado neste mês.'))
    if not parcelas.empty:
        for _,p in parcelas.iterrows():
            try:
                at=int(p.get("ParcelaAtual",0)); tot=int(p.get("TotalParcelas",0))
                if tot>0 and tot-at<=2: res.append(("info","✅ Parcela encerrando",f'"{p.get("Descricao","")}" — {at}/{tot}. Quase quitado!'))
            except: pass
    if not res: res.append(("ok","✅ Tudo em ordem","Nenhum alerta financeiro."))
    return res

# ══════════════════════════════════════════
# FUNÇÃO DE VOZ — WHISPER + GPT-4o-mini
# ══════════════════════════════════════════
def resolver_data(texto_data: str) -> str:
    """Converte expressões relativas em datas reais."""
    t = texto_data.lower().strip()
    if not t or t in ("hoje", "today", ""):
        return str(hoje.date())
    if t in ("ontem", "yesterday"):
        return str((hoje - timedelta(days=1)).date())
    if "semana passada" in t or "semana anterior" in t:
        return str((hoje - timedelta(days=7)).date())
    if "anteontem" in t:
        return str((hoje - timedelta(days=2)).date())
    # tenta parse direto
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m"):
        try:
            d = datetime.strptime(t, fmt)
            if d.year == 1900:
                d = d.replace(year=hoje.year)
            return str(d.date())
        except:
            pass
    return str(hoje.date())

def transcrever_audio(audio_bytes: bytes, api_key: str) -> str:
    """Envia áudio ao Whisper e retorna transcrição em PT."""
    client = OpenAI(api_key=api_key)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="pt",
                response_format="text"
            )
        return str(resp).strip()
    finally:
        os.unlink(tmp_path)

def buscar_cotacao(moeda="USD") -> float:
    """Busca cotação em tempo real via API pública gratuita."""
    try:
        import urllib.request
        url = f"https://economia.awesomeapi.com.br/json/last/{moeda}-BRL"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            return float(data[f"{moeda}BRL"]["bid"])
    except Exception:
        fallback = {"USD": 5.70, "EUR": 6.20, "GBP": 7.20, "ARS": 0.006}
        return fallback.get(moeda, 1.0)

def extrair_lancamento(transcricao: str, api_key: str,
                       categorias: list, pessoas: list) -> dict:
    """GPT-4o-mini lê a transcrição e extrai campos estruturados."""
    client = OpenAI(api_key=api_key)

    prompt_sistema = f"""Você é um assistente financeiro. A partir de uma frase em português falada pelo usuário,
extraia as informações de um lançamento financeiro e retorne SOMENTE um JSON válido com os campos abaixo.

Campos obrigatórios:
- "descricao": string resumida do gasto/receita
- "valor": número float — se for parcelado, é o VALOR TOTAL (ex: "5 mil em 12x" → 5000.0)
- "moeda": "BRL", "USD", "EUR", "GBP" ou "ARS"
- "tipo": "Saída" ou "Entrada"
- "pessoa": uma de {pessoas} — padrão "{pessoas[0]}"
- "categoria": mais adequada entre: {json.dumps(categorias, ensure_ascii=False)}
- "data_texto": expressão de data ("hoje", "ontem", "semana passada") ou ""
- "confianca": 0-100
- "parcelas_total": número inteiro de parcelas se mencionado (ex: "12x" → 12), ou 0 se não parcelado
- "parcelas_atual": parcela atual se mencionado (ex: "estou pagando a 3ª" → 3), ou 0 se não informado

Regras de categoria:
- "mercado", "supermercado", "feira" → "Supermercado / Feira"
- "gasolina", "combustível", "abasteci" → "Combustível"
- "farmácia", "remédio" → "Farmácia"
- "restaurante", "almoço", "jantar", "delivery" → "Restaurante / Delivery"
- "máquina de lavar", "geladeira", "TV", "celular", "notebook" → "Eletrônicos / Tecnologia"
- Se não conseguir extrair o valor → "valor": 0
- Se a moeda não for mencionada → "BRL"
- Retorne APENAS o JSON, sem markdown, sem explicação."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user",   "content": transcricao}
        ],
        temperature=0,
        max_tokens=300
    )

    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    dados = json.loads(raw)

    # ── Conversão automática de moeda para BRL ──
    moeda = dados.get("moeda", "BRL").upper()
    if moeda != "BRL" and dados.get("valor", 0) > 0:
        cotacao = buscar_cotacao(moeda)
        valor_original = dados["valor"]
        dados["valor"] = round(valor_original * cotacao, 2)
        dados["descricao"] = f"{dados.get('descricao','')} ({valor_original} {moeda} × {cotacao:.2f})"
        dados["_cotacao_info"] = f"1 {moeda} = R$ {cotacao:.2f}"

    return dados

def widget_voz(categorias_despesa, categorias_receita, pessoas):
    """Renderiza o widget de lançamento por voz no Painel Geral."""

    # ── Verificações de dependências ──
    if not AUDIO_OK:
        st.markdown("""<div class="alert-card warn">
            <div class="alert-icon">⚠️</div>
            <div><div class="alert-title">Atualize o Streamlit para usar voz</div>
            <div class="alert-msg"><code>pip install streamlit --upgrade</code></div></div>
        </div>""", unsafe_allow_html=True)
        return

    if not OPENAI_OK:
        st.markdown("""<div class="alert-card warn">
            <div class="alert-icon">📦</div>
            <div><div class="alert-title">Instale o pacote OpenAI</div>
            <div class="alert-msg"><code>pip install openai</code></div></div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Chave API ──
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "🔑 OpenAI API Key", type="password",
            placeholder="sk-...", key="oai_key",
            help="Cole sua chave. Ou salve em .streamlit/secrets.toml"
        )

    if not api_key:
        st.markdown("""<div class="alert-card info">
            <div class="alert-icon">🔑</div>
            <div><div class="alert-title">Informe sua chave OpenAI acima</div>
            <div class="alert-msg">Ou adicione ao <code>.streamlit/secrets.toml</code>:<br>
            <code>OPENAI_API_KEY = "sk-..."</code></div></div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Dicas de uso ──
    st.markdown("""<div style="background:var(--accent-dim);border:1px solid rgba(41,217,245,.22);
        border-radius:12px;padding:.9rem 1.2rem;margin-bottom:.75rem;font-size:.84rem;color:var(--text-sec);">
        🎙️ <b style="color:var(--accent);">Exemplos:</b>
        "Gastei 80 reais no mercado hoje" &nbsp;·&nbsp;
        "Isabela foi ao médico ontem, 350 reais" &nbsp;·&nbsp;
        "Abasteci o carro, 180 reais"
    </div>""", unsafe_allow_html=True)

    # ── Gravador nativo do Streamlit (sem dependência externa) ──
    if "voz_reset" not in st.session_state:
        st.session_state.voz_reset = 0

    audio_file = st.audio_input(
        "🎙️ Clique para gravar sua despesa",
        key=f"audio_{st.session_state.voz_reset}"
    )

    audio_bytes = None
    if audio_file is not None:
        audio_bytes = audio_file.read()
        st.audio(audio_bytes, format="audio/wav")

    if audio_bytes:
        with st.spinner("🎙️ Transcrevendo com Whisper..."):
            try:
                transcricao = transcrever_audio(audio_bytes, api_key)
            except Exception as e:
                st.error(f"❌ Erro na transcrição: {e}")
                return

        st.markdown(f"""<div style="background:var(--surface);border:1px solid var(--border);
            border-radius:10px;padding:.75rem 1rem;margin:.5rem 0;">
            <span style="font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">
            Você disse:</span><br>
            <span style="font-size:.95rem;color:var(--text);">"{transcricao}"</span>
        </div>""", unsafe_allow_html=True)

        with st.spinner("🧠 IA extraindo informações..."):
            try:
                dados = extrair_lancamento(
                    transcricao, api_key,
                    categorias_despesa + categorias_receita,
                    pessoas
                )
            except Exception as e:
                st.error(f"❌ Erro na extração: {e}")
                return

        data_final  = resolver_data(dados.get("data_texto", ""))
        confianca   = int(dados.get("confianca", 0))
        parc_total  = int(dados.get("parcelas_total", 0))
        parc_atual  = int(dados.get("parcelas_atual", 0))
        é_parcelado = parc_total > 1

        cor_conf = "ok" if confianca >= 80 else "warn" if confianca >= 60 else "error"
        ico_conf = "✅" if confianca >= 80 else "⚠️" if confianca >= 60 else "🔴"
        cotacao_info = dados.get("_cotacao_info","")

        st.markdown(f"""<div class="alert-card {cor_conf}" style="margin-top:.75rem;">
            <div class="alert-icon">{ico_conf}</div>
            <div style="flex:1;">
                <div class="alert-title">{'💳 Compra parcelada detectada!' if é_parcelado else 'IA extraiu — confirme antes de lançar'}</div>
                <div class="alert-msg">Confiança: <b>{confianca}%</b>
                {f' &nbsp;·&nbsp; 💱 <b>{cotacao_info}</b>' if cotacao_info else ''}
                {f' &nbsp;·&nbsp; 💳 <b>{parc_total}x</b> de R$ {dados.get("valor",0)/parc_total:,.2f}' if é_parcelado else ''}
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── Se for parcelado, pergunta qual parcela está pagando ──
        if é_parcelado:
            st.markdown("""<div style="background:var(--accent2-dim);border:1px solid rgba(139,92,246,.25);
                border-radius:12px;padding:1rem 1.2rem;margin:.5rem 0;">
                <b style="color:var(--accent2);">💳 Compra parcelada detectada!</b>
                <span style="color:var(--text-sec);font-size:.86rem;"> Informe qual parcela você está pagando agora:</span>
            </div>""", unsafe_allow_html=True)

            pp1, pp2, pp3 = st.columns(3)
            with pp1:
                parc_atual_v = st.number_input(
                    "📌 Parcela atual (que está pagando)",
                    min_value=1, max_value=parc_total,
                    value=max(parc_atual, 1),
                    key="voz_parc_atual"
                )
            with pp2:
                parc_total_v = st.number_input(
                    "🔢 Total de parcelas",
                    min_value=1, max_value=120,
                    value=parc_total,
                    key="voz_parc_total"
                )
            with pp3:
                valor_parc = dados.get("valor", 0) / parc_total_v if parc_total_v > 0 else 0
                st.markdown(f"""<div style="background:var(--accent-dim);border-radius:9px;
                    padding:.75rem 1rem;border:1px solid rgba(41,217,245,.15);margin-top:1.5rem;">
                    <span style="color:var(--muted);font-size:.76rem;">VALOR POR PARCELA</span><br>
                    <span style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;
                    color:var(--accent);">R$ {valor_parc:,.2f}</span>
                </div>""", unsafe_allow_html=True)

            parcelas_restantes = parc_total_v - parc_atual_v
            if parcelas_restantes > 0:
                st.info(f"📆 Serão criadas **{parcelas_restantes}** parcela(s) futuras automaticamente (da {parc_atual_v+1}ª até a {parc_total_v}ª).")

        # ── Se NÃO for parcelado, campos editáveis normais ──
        if not é_parcelado:
            parc_total_v = 1
            parc_atual_v = 1
        c1, c2 = st.columns(2)
        with c1:
            try:
                data_val = datetime.strptime(data_final, "%Y-%m-%d").date()
            except Exception:
                data_val = hoje.date()
            data_v   = st.date_input("📅 Data", value=data_val, key="voz_data")
            pessoa_v = st.selectbox("👤 Pessoa", pessoas,
                index=pessoas.index(dados["pessoa"]) if dados.get("pessoa") in pessoas else 0,
                key="voz_pessoa")
            tipo_v   = st.selectbox("↕️ Tipo", ["Saída","Entrada"],
                index=0 if dados.get("tipo","Saída")=="Saída" else 1,
                key="voz_tipo")
        with c2:
            desc_v  = st.text_input("📝 Descrição",
                value=dados.get("descricao",""), key="voz_desc")
            valor_label = "💰 Valor total (R$)" if é_parcelado else "💰 Valor (R$)"
            valor_v = st.number_input(valor_label,
                value=float(dados.get("valor", 0.0)),
                min_value=0.0, format="%.2f", key="voz_valor")
            lista_cat = categorias_despesa if tipo_v=="Saída" else categorias_receita
            cat_sug   = dados.get("categoria","")
            idx_cat   = lista_cat.index(cat_sug) if cat_sug in lista_cat else 0
            cat_v     = st.selectbox("🏷️ Categoria", lista_cat,
                index=idx_cat, key="voz_cat")

        # ── Botões ──
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            label_btn = f"✅ Confirmar e criar {parc_total_v if é_parcelado else 1} lançamento(s)" if é_parcelado else "✅ Confirmar e Lançar"
            if st.button(label_btn, use_container_width=True, key="voz_ok"):
                if not desc_v:
                    st.warning("⚠️ Informe a descrição.")
                elif valor_v == 0:
                    st.warning("⚠️ Valor deve ser maior que zero.")
                else:
                    if é_parcelado:
                        # Cria parcela atual + todas as futuras
                        lns = []
                        vp  = valor_v / parc_total_v
                        data_base = datetime.strptime(str(data_v), "%Y-%m-%d")
                        for p in range(parc_atual_v, parc_total_v + 1):
                            offset = p - parc_atual_v
                            mes_p  = (data_base.month + offset - 1) % 12 + 1
                            ano_p  = data_base.year + (data_base.month + offset - 1) // 12
                            dt_p   = datetime(ano_p, mes_p, data_base.day).strftime("%Y-%m-%d")
                            lns.append([dt_p, pessoa_v, cat_v,
                                        f"{desc_v} ({p}/{parc_total_v})", round(vp, 2), tipo_v])
                        inserir(lns)
                        # Registra no controle de parcelas
                        ws["parcelas"].append_row([
                            desc_v, cat_v, round(vp,2), parc_total_v,
                            parc_atual_v, pessoa_v, str(data_v)
                        ])
                        st.success(f"✅ **{desc_v}** — {parc_total_v - parc_atual_v + 1} parcelas de R$ {vp:,.2f} criadas! 💳")
                    else:
                        inserir([[str(data_v), pessoa_v, cat_v, desc_v, valor_v, tipo_v]])
                        st.success(f"✅ **{desc_v}** — R$ {valor_v:,.2f} lançado via voz! 🎙️")
                    st.session_state.voz_reset += 1
                    time.sleep(1)
                    st.rerun()
        with col_cancel:
            if st.button("❌ Cancelar", use_container_width=True, key="voz_cancel"):
                st.session_state.voz_reset += 1
                st.rerun()


# ══════════════════════════════════════════
# METAS MENSAIS
# ══════════════════════════════════════════
ALERTA_META_PCT = 80  # alerta em 80%

def get_metas_mes(mes, ano):
    """Retorna dict {categoria: valor_meta} para o mês/ano."""
    if metas.empty: return {}
    m = metas.copy()
    for c in ["Mes","Ano","ValorMeta"]:
        if c not in m.columns: return {}
    m["Mes"] = pd.to_numeric(m["Mes"], errors="coerce")
    m["Ano"] = pd.to_numeric(m["Ano"], errors="coerce")
    m["ValorMeta"] = m["ValorMeta"].apply(converter_valor)
    filtro = m[(m["Mes"]==mes) & (m["Ano"]==ano)]
    if filtro.empty:
        # Tenta meta genérica (sem mês específico, Mes=0)
        filtro = m[m["Mes"]==0]
    return dict(zip(filtro["Categoria"], filtro["ValorMeta"]))

def salvar_meta(categoria, valor, mes, ano):
    """Salva ou atualiza meta na planilha."""
    try:
        todos = ws["metas"].get_all_records()
        for i, r in enumerate(todos):
            if (str(r.get("Categoria",""))==categoria and
                str(r.get("Mes",""))==str(mes) and
                str(r.get("Ano",""))==str(ano)):
                ws["metas"].update(f"B{i+2}", [[valor]])
                load_metas.clear()
                return
        ws["metas"].append_row([categoria, valor, mes, ano])
        load_metas.clear()
    except Exception as e:
        st.error(f"❌ Erro ao salvar meta: {e}")

def alertas_metas(df_mes, mes, ano):
    """Gera alertas de metas para o mês."""
    metas_mes = get_metas_mes(mes, ano)
    alertas_list = []
    for cat, meta in metas_mes.items():
        if meta <= 0: continue
        gasto = df_mes[df_mes["Categoria"]==cat]["Valor"].sum() if not df_mes.empty else 0
        pct = gasto / meta * 100
        if pct >= 100:
            alertas_list.append(("error", f"🔴 Meta estourada: {cat}",
                f"Gasto R$ {gasto:,.2f} de R$ {meta:,.2f} ({pct:.0f}%)"))
        elif pct >= ALERTA_META_PCT:
            alertas_list.append(("warn", f"⚠️ Meta em {pct:.0f}%: {cat}",
                f"Gasto R$ {gasto:,.2f} de R$ {meta:,.2f} — faltam R$ {meta-gasto:,.2f}"))
    return alertas_list

# ══════════════════════════════════════════
# PROJEÇÃO DE FLUXO DE CAIXA
# ══════════════════════════════════════════
def projetar_fluxo(df, fixos, parcelas, meses_ahead=3):
    """
    Projeta receitas e despesas para os próximos N meses.
    Lógica:
    - Receita: média dos últimos 3 meses com entrada
    - Despesas variáveis: média dos últimos 3 meses de saída
    - Fixos: soma dos fixos cadastrados (recorrentes garantidos)
    - Parcelas: soma das parcelas ainda ativas
    """
    hoje_dt = datetime.today()
    resultado = []

    # Calcula médias históricas (últimos 3 meses)
    df_hist = df.copy()
    df_hist["_dt"] = pd.to_datetime(df_hist["Data"], errors="coerce")
    df_hist = df_hist.dropna(subset=["_dt"])

    medias_rec  = []
    medias_desp = []
    for i in range(1, 4):
        m = (hoje_dt.month - i - 1) % 12 + 1
        a = hoje_dt.year - ((hoje_dt.month - i - 1) // 12 + 1) + (0 if (hoje_dt.month-i)>0 else 0)
        if (hoje_dt.month - i) <= 0: a = hoje_dt.year - 1
        else: a = hoje_dt.year
        dm = df_hist[(df_hist["_dt"].dt.month==m)&(df_hist["_dt"].dt.year==a)]
        medias_rec.append(dm[dm["Tipo"]=="Entrada"]["Valor"].sum())
        medias_desp.append(dm[dm["Tipo"]=="Saída"]["Valor"].sum())

    media_rec  = sum(medias_rec) / max(len([x for x in medias_rec if x>0]), 1)
    media_desp = sum(medias_desp) / max(len([x for x in medias_desp if x>0]), 1)

    # Soma fixos recorrentes
    total_fixos = 0
    if not fixos.empty and "Valor" in fixos.columns:
        total_fixos = fixos["Valor"].apply(converter_valor).sum()

    # Soma parcelas ativas por mês
    parc_por_mes = {}
    if not parcelas.empty:
        for _, p in parcelas.iterrows():
            try:
                at  = int(p.get("ParcelaAtual", 0))
                tot = int(p.get("TotalParcelas", 0))
                val = converter_valor(p.get("Valor", 0))
                dt_ini = pd.to_datetime(p.get("DataInicio",""), errors="coerce")
                if pd.isna(dt_ini): continue
                for offset in range(tot - at + 1):
                    m_p = (dt_ini.month + at - 1 + offset - 1) % 12 + 1
                    a_p = dt_ini.year + (dt_ini.month + at - 1 + offset - 1) // 12
                    chave = (a_p, m_p)
                    parc_por_mes[chave] = parc_por_mes.get(chave, 0) + val
            except: pass

    saldo_acum = df["Valor"][df["Tipo"]=="Entrada"].sum() - df["Valor"][df["Tipo"]=="Saída"].sum() \
                 if not df.empty else 0

    for i in range(1, meses_ahead + 1):
        m_fut = (hoje_dt.month + i - 1) % 12 + 1
        a_fut = hoje_dt.year + (hoje_dt.month + i - 1) // 12
        label = f"{MESES_PT[m_fut-1][:3]}/{a_fut}"

        parc_mes = parc_por_mes.get((a_fut, m_fut), 0)
        desp_proj = media_desp + total_fixos + parc_mes
        rec_proj  = media_rec

        saldo_acum += rec_proj - desp_proj
        resultado.append({
            "label":     label,
            "mes":       m_fut,
            "ano":       a_fut,
            "receita":   rec_proj,
            "despesa":   desp_proj,
            "fixos":     total_fixos,
            "parcelas":  parc_mes,
            "variavel":  media_desp,
            "saldo_acum":saldo_acum,
        })

    return resultado

# ══════════════════════════════════════════
# TABS
# ══════════════════════════════════════════
tabs=st.tabs(["🏠 Painel Geral","📊 Dashboard","➕ Lançamentos","💚 Receitas",
              "🏦 OFX · IA","📄 PDF","📥 CSV","⚙️ Fixos","💳 Parcelas",
              "🎯 Metas","📈 Projeção","💹 Investimentos","🏛️ Patrimônio","📦 Bens"])

# ══════════════════════════════════════════
# TAB 0 — PAINEL GERAL
# ══════════════════════════════════════════
with tabs[0]:
    df["_dt"]=pd.to_datetime(df["Data"],errors="coerce")
    ma,ya=hoje.month,hoje.year
    dm=df[(df["_dt"].dt.month==ma)&(df["_dt"].dt.year==ya)]
    rec_m=dm[dm["Tipo"]=="Entrada"]["Valor"].sum()
    desp_m=dm[dm["Tipo"]=="Saída"]["Valor"].sum()
    saldo_m=rec_m-desp_m
    pct_c=(desp_m/rec_m*100) if rec_m>0 else 0

    # ── Diagnóstico temporário ──
    with st.expander("🔍 Diagnóstico de dados (clique para ver)"):
        raw = ws["lanc"].get_all_records()
        st.write("**3 primeiros registros RAW da planilha:**")
        st.write(raw[:3])
        st.write(f"**Soma total Valor após conversão:** {df['Valor'].sum()}")
        st.write(f"**Valores únicos (amostra):** {df['Valor'].unique()[:10]}")

    st.markdown(f'<div class="section-title">📅 {MESES_PT[ma-1]} {ya} — Resumo do Mês</div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    for col,cor,ico,lab,val,sub in [
        (c1,"green","💚","Receita do Mês",f"R$ {rec_m:,.2f}","Entradas registradas"),
        (c2,"red","🔴","Despesa do Mês",f"R$ {desp_m:,.2f}","Saídas registradas"),
        (c3,"blue" if saldo_m>=0 else "red","💰","Saldo do Mês",f"R$ {saldo_m:,.2f}","✅ Positivo" if saldo_m>=0 else "⚠️ Negativo"),
        (c4,"yellow","📊","Comprometido",f"{pct_c:.0f}%",f"R$ {desp_m:,.2f} / R$ {rec_m:,.2f}"),
        (c5,"purple","📦","Lançamentos",str(len(dm)),f"{len(df)} total geral"),
    ]:
        with col:
            st.markdown(f'<div class="kpi-card {cor}"><span class="kpi-icon">{ico}</span><div class="kpi-label">{lab}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)

    pc=min(pct_c,100); cc="#22d3a0" if pct_c<70 else "#fbbf24" if pct_c<90 else "#f8625a"
    st.markdown(f'<div style="margin:.8rem 0 1.5rem;"><div style="display:flex;justify-content:space-between;font-size:.76rem;color:var(--muted);margin-bottom:.3rem;"><span>Orçamento mensal consumido</span><span>{pct_c:.1f}%</span></div><div class="prog-bar"><div class="prog-fill" style="width:{pc:.1f}%;background:{cc};"></div></div></div>',unsafe_allow_html=True)

    # ── BOTÃO RELATÓRIO PDF ──
    st.markdown('<div class="section-title">📄 Relatório Mensal</div>', unsafe_allow_html=True)
    col_rel1, col_rel2, col_rel3 = st.columns([1,1,2])
    with col_rel1:
        mes_rel = st.selectbox("Mês", list(range(1,13)),
            index=ma-1, format_func=lambda x: MESES_PT[x-1], key="rel_mes")
    with col_rel2:
        ano_rel = st.number_input("Ano", min_value=2020, max_value=2030,
            value=ya, step=1, key="rel_ano")
    with col_rel3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📄 Gerar Relatório PDF", use_container_width=True, key="btn_pdf"):
            with st.spinner(f"📊 Gerando relatório de {MESES_PT[mes_rel-1]}/{ano_rel}..."):
                try:
                    import subprocess, sys
                    result = subprocess.run(
                        [sys.executable, "relatorio.py", str(ano_rel), str(mes_rel)],
                        capture_output=True, text=True, cwd=os.getcwd()
                    )
                    nome_pdf = f"Relatorio_Financeiro_{MESES_PT[mes_rel-1]}_{ano_rel}.pdf"
                    if os.path.exists(nome_pdf):
                        with open(nome_pdf, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Baixar {nome_pdf}",
                                data=f.read(),
                                file_name=nome_pdf,
                                mime="application/pdf",
                                key="download_pdf"
                            )
                        st.success(f"✅ Relatório de {MESES_PT[mes_rel-1]}/{ano_rel} gerado!")
                    else:
                        st.error(f"❌ Erro: {result.stderr[:300]}")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── ATALHO RÁPIDO DE VOZ ──
    st.markdown('<div class="section-title">🎙️ Lançamento Rápido por Voz</div>', unsafe_allow_html=True)
    widget_voz(cat_desp, cat_rec, pessoas)
    st.markdown("<br>", unsafe_allow_html=True)

    col_esq,col_dir=st.columns([3,2])

    with col_dir:
        st.markdown('<div class="section-title">🔔 Alertas Inteligentes</div>',unsafe_allow_html=True)
        tmap={"error":("🔴","error"),"warn":("🟡","warn"),"ok":("🟢","ok"),"info":("🔵","info")}

        # Alertas financeiros gerais
        for tipo,titulo,msg in alertas(df.copy(),fixos,parcelas):
            ico_a,cls_a=tmap.get(tipo,("ℹ️","info"))
            st.markdown(f'<div class="alert-card {cls_a}"><div class="alert-icon">{ico_a}</div><div><div class="alert-title">{titulo}</div><div class="alert-msg">{msg}</div></div></div>',unsafe_allow_html=True)

        # Alertas de metas
        alertas_m = alertas_metas(dm, ma, ya)
        if alertas_m:
            for tipo,titulo,msg in alertas_m:
                ico_a,cls_a=tmap.get(tipo,("ℹ️","info"))
                st.markdown(f'<div class="alert-card {cls_a}"><div class="alert-icon">{ico_a}</div><div><div class="alert-title">{titulo}</div><div class="alert-msg">{msg}</div></div></div>',unsafe_allow_html=True)

        # ── Metas do mês ──
        metas_mes = get_metas_mes(ma, ya)
        if metas_mes:
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown('<div class="section-title">🎯 Metas do Mês</div>',unsafe_allow_html=True)
            for cat, meta in metas_mes.items():
                gasto = dm[dm["Categoria"]==cat]["Valor"].sum() if not dm.empty else 0
                pct_m = min(gasto/meta*100, 100) if meta>0 else 0
                cor_m = "#22d3a0" if pct_m<80 else "#fbbf24" if pct_m<100 else "#f8625a"
                st.markdown(f"""<div style="padding:.5rem .75rem;margin:.25rem 0;background:var(--surface);border-radius:8px;border-left:3px solid {cor_m};">
                    <div style="display:flex;justify-content:space-between;margin-bottom:.25rem;">
                        <span style="font-size:.82rem;">🎯 {cat}</span>
                        <span style="font-size:.78rem;color:{cor_m};font-weight:700;">R$ {gasto:,.2f} / R$ {meta:,.2f}</span>
                    </div>
                    <div class="prog-bar" style="height:5px;"><div class="prog-fill" style="width:{pct_m:.0f}%;background:{cor_m};"></div></div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 Fixos & Parcelas Ativos</div>',unsafe_allow_html=True)
        if not fixos.empty:
            for _,f in fixos.iterrows():
                venc=f.get("DiaVencimento","—"); val=float(f.get("Valor",0) or 0)
                st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem .75rem;margin:.25rem 0;background:var(--surface);border-radius:8px;border-left:3px solid var(--yellow);"><span style="font-size:.84rem;">🔁 {f.get("Descricao","")}</span><span style="font-size:.82rem;color:var(--yellow);font-weight:700;">R$ {val:,.2f} <span style="color:var(--muted);font-weight:400;">· dia {venc}</span></span></div>',unsafe_allow_html=True)
        if not parcelas.empty:
            for _,p in parcelas.iterrows():
                try:
                    at=int(p.get("ParcelaAtual",0)); tot=int(p.get("TotalParcelas",1)); pcp=at/tot*100
                    pc2="#22d3a0" if pcp<70 else "#fbbf24" if pcp<90 else "#f8625a"
                    st.markdown(f'<div style="padding:.5rem .75rem;margin:.25rem 0;background:var(--surface);border-radius:8px;border-left:3px solid var(--accent2);"><div style="display:flex;justify-content:space-between;margin-bottom:.25rem;"><span style="font-size:.84rem;">💳 {p.get("Descricao","")}</span><span style="font-size:.78rem;color:var(--accent2);font-weight:700;">{at}/{tot}</span></div><div class="prog-bar" style="height:5px;"><div class="prog-fill" style="width:{pcp:.0f}%;background:{pc2};"></div></div></div>',unsafe_allow_html=True)
                except: pass

    with col_esq:
        st.markdown('<div class="section-title">📆 Evolução Mensal</div>',unsafe_allow_html=True)
        dfe=df.copy(); dfe["_dt"]=pd.to_datetime(dfe["Data"],errors="coerce"); dfe=dfe.dropna(subset=["_dt"])
        dfe["Mês"]=dfe["_dt"].dt.to_period("M").astype(str)
        dfeg=dfe.groupby(["Mês","Tipo"])["Valor"].sum().reset_index()
        if not dfeg.empty:
            fig=px.bar(dfeg,x="Mês",y="Valor",color="Tipo",barmode="group",color_discrete_map={"Entrada":"#22d3a0","Saída":"#f8625a"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",legend=dict(bgcolor="rgba(0,0,0,0)"),xaxis=dict(gridcolor="#2a3a5c",title=""),yaxis=dict(gridcolor="#2a3a5c",title="R$"),margin=dict(t=5,b=5,l=0,r=0),height=240)
            st.plotly_chart(fig,use_container_width=True)

        st.markdown('<div class="section-title">🗓️ Calendário de Vencimentos</div>',unsafe_allow_html=True)
        dias_lanc=set(dm["_dt"].dt.day.dropna().astype(int).tolist())
        dias_fix=set()
        if not fixos.empty and "DiaVencimento" in fixos.columns:
            for v in fixos["DiaVencimento"]:
                try: dias_fix.add(int(v))
                except: pass
        pdia=date(ya,ma,1); off=(pdia.weekday()+1)%7; ult=calendar.monthrange(ya,ma)[1]
        cal='<div class="cal-grid">'
        for ds in ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]:
            cal+=f'<div style="text-align:center;font-size:.68rem;color:var(--muted);font-weight:700;padding:.3rem 0;">{ds}</div>'
        for _ in range(off): cal+='<div></div>'
        for d in range(1,ult+1):
            cls=" today" if d==hoje.day else " has-event" if d in dias_fix else ""
            dots=(''.join(['<div class="cal-dot green"></div>' if d in dias_lanc else '','<div class="cal-dot red"></div>' if d in dias_fix else '']))
            cal+=f'<div class="cal-day{cls}"><span class="cal-num">{d}</span>{dots}</div>'
        cal+="</div>"
        st.markdown(cal,unsafe_allow_html=True)
        st.markdown('<div style="display:flex;gap:1rem;margin-top:.6rem;font-size:.72rem;color:var(--muted);"><span><span style="color:var(--green);">●</span> Lançamento</span><span><span style="color:var(--red);">●</span> Fixo</span><span style="color:var(--accent);">■ Hoje</span></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏆 Top Despesas do Mês</div>',unsafe_allow_html=True)
    dfsm=dm[dm["Tipo"]=="Saída"]
    if not dfsm.empty:
        top=dfsm.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).head(8).reset_index()
        fig2=px.bar(top,x="Valor",y="Categoria",orientation="h",color="Valor",color_continuous_scale=["#1a2540","#29d9f5"])
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",showlegend=False,coloraxis_showscale=False,yaxis=dict(autorange="reversed"),xaxis=dict(gridcolor="#2a3a5c",title="R$"),margin=dict(t=5,b=5,l=0,r=0),height=260)
        st.plotly_chart(fig2,use_container_width=True)
    else: st.info("Nenhuma despesa neste mês.")

    st.markdown('<div class="section-title">📋 Todos os Lançamentos do Mês</div>',unsafe_allow_html=True)
    df_mes_tab = dm.drop(columns=["_dt"],errors="ignore").sort_values("Data",ascending=False)
    tabela_com_excluir(df_mes_tab, key_prefix="painel")

# ══════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════
with tabs[1]:
    rec_o=df[(df["Tipo"]=="Entrada")&(df["Pessoa"]=="Octavio")]["Valor"].sum()
    rec_i=df[(df["Tipo"]=="Entrada")&(df["Pessoa"]=="Isabela")]["Valor"].sum()
    rec=df[df["Tipo"]=="Entrada"]["Valor"].sum(); desp=df[df["Tipo"]=="Saída"]["Valor"].sum(); saldo=rec-desp
    st.markdown('<div class="section-title">📊 Visão Geral — Todos os Períodos</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    for col,cor,lab,val,sub in [(c1,"green","Receita Total",f"R$ {rec:,.2f}",f"Oct R${rec_o:,.0f} · Isa R${rec_i:,.0f}"),
        (c2,"red","Despesa Total",f"R$ {desp:,.2f}","Total saídas"),
        (c3,"blue" if saldo>=0 else "red","Saldo Acumulado",f"R$ {saldo:,.2f}",f"{desp/rec*100:.0f}% comprometido" if rec>0 else "—"),
        (c4,"purple","Registros",str(len(df)),f"{len(df)} lançamentos")]:
        with col: st.markdown(f'<div class="kpi-card {cor}"><div class="kpi-label">{lab}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    cg1,cg2=st.columns(2)
    with cg1:
        st.markdown('<div class="section-title">🍩 Por Grupo</div>',unsafe_allow_html=True)
        dfs=df[df["Tipo"]=="Saída"].copy()
        if not dfs.empty:
            def gd(c):
                for g,cs in GRUPOS.items():
                    if c in cs: return g.split(" ",1)[1] if " " in g else g
                return "Outros"
            dfs["Grupo"]=dfs["Categoria"].apply(gd)
            fig=px.pie(dfs,names="Grupo",values="Valor",hole=.45,color_discrete_sequence=["#29d9f5","#8b5cf6","#22d3a0","#fbbf24","#f8625a","#c084fc","#34d399","#fb923c"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=11)),margin=dict(t=5,b=5,l=0,r=0))
            st.plotly_chart(fig,use_container_width=True)
    with cg2:
        st.markdown('<div class="section-title">📆 Receita vs Despesa</div>',unsafe_allow_html=True)
        dft=df.copy(); dft["_dt"]=pd.to_datetime(dft["Data"],errors="coerce"); dft=dft.dropna(subset=["_dt"]); dft["Mês"]=dft["_dt"].dt.to_period("M").astype(str)
        dfmg=dft.groupby(["Mês","Tipo"])["Valor"].sum().reset_index()
        if not dfmg.empty:
            fig=px.bar(dfmg,x="Mês",y="Valor",color="Tipo",barmode="group",color_discrete_map={"Entrada":"#22d3a0","Saída":"#f8625a"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",legend=dict(bgcolor="rgba(0,0,0,0)"),xaxis=dict(gridcolor="#2a3a5c"),yaxis=dict(gridcolor="#2a3a5c"),margin=dict(t=5,b=5,l=0,r=0))
            st.plotly_chart(fig,use_container_width=True)
    st.markdown('<div class="section-title">📋 Lançamentos Recentes</div>',unsafe_allow_html=True)

    # ── Botão limpar planilha ──
    with st.expander("⚠️ Zona de perigo — Limpar planilha"):
        st.markdown('<div style="color:var(--red);font-size:.85rem;margin-bottom:.75rem;">Esta ação apaga <b>TODOS</b> os lançamentos permanentemente. Não há como desfazer!</div>',unsafe_allow_html=True)
        if "confirm_limpar" not in st.session_state:
            st.session_state.confirm_limpar = False
        if not st.session_state.confirm_limpar:
            if st.button("🗑️ Limpar todos os lançamentos", key="btn_limpar"):
                st.session_state.confirm_limpar = True
                st.rerun()
        else:
            st.warning("⚠️ Tem certeza? Esta ação é irreversível!")
            cl1,cl2 = st.columns(2)
            if cl1.button("✅ SIM, apagar tudo", key="btn_limpar_ok"):
                if limpar_planilha():
                    st.session_state.confirm_limpar = False
                    st.success("✅ Planilha limpa! Pronto para novos lançamentos.")
                    st.rerun()
            if cl2.button("❌ Cancelar", key="btn_limpar_cancel"):
                st.session_state.confirm_limpar = False
                st.rerun()

    df_tab = df.drop(columns=["_dt"],errors="ignore").sort_values("Data",ascending=False).head(100)
    tabela_com_excluir(df_tab, key_prefix="dash")

# ══════════════════════════════════════════
# TAB 2 — LANÇAMENTOS
# ══════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">➕ Novo Lançamento Manual</div>',unsafe_allow_html=True)
    with st.form("form_lanc",clear_on_submit=True):
        c1,c2=st.columns(2)
        with c1: data_l=st.date_input("📅 Data",value=hoje); pessoa_l=st.selectbox("👤 Pessoa",pessoas); tipo_l=st.selectbox("↕️ Tipo",["Saída","Entrada"])
        with c2:
            desc_l=st.text_input("📝 Descrição"); valor_l=st.number_input("💰 Valor (R$)",min_value=0.0,format="%.2f")
            o=opts_ui(despesa=(tipo_l=="Saída"),receita=(tipo_l=="Entrada")); cr=st.selectbox("🏷️ Categoria",o); cat_l=limpa(cr)
        if st.form_submit_button("💾 Salvar",use_container_width=True):
            if not desc_l: st.warning("⚠️ Informe a descrição.")
            elif valor_l==0: st.warning("⚠️ Valor maior que zero.")
            elif not cat_l: st.warning("⚠️ Categoria válida.")
            else: inserir([[str(data_l),pessoa_l,cat_l,desc_l,valor_l,tipo_l]]); st.success(f"✅ {desc_l} — R$ {valor_l:,.2f}"); st.rerun()

# ══════════════════════════════════════════
# TAB 3 — RECEITAS
# ══════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">💚 Gestão de Receitas</div>',unsafe_allow_html=True)
    sr=st.tabs(["💰 Salários","✨ Receita Variável"])
    with sr[0]:
        co,ci=st.columns(2)
        with co: sal_o=st.number_input("💰 Salário Octavio",min_value=0.0,format="%.2f",key="so"); dato=st.date_input("📅 Data",value=hoje,key="do")
        with ci: sal_i=st.number_input("💰 Salário Isabela",min_value=0.0,format="%.2f",key="si"); dati=st.date_input("📅 Data",value=hoje,key="di")
        if st.button("⚡ Lançar Salários do Mês",use_container_width=True):
            lns=[]
            if sal_o>0: lns.append([str(dato),"Octavio","Salário Octavio","Salário Mensal",sal_o,"Entrada"])
            if sal_i>0: lns.append([str(dati),"Isabela","Salário Isabela","Salário Mensal",sal_i,"Entrada"])
            if lns: inserir(lns); st.success(f"✅ Total: R$ {sal_o+sal_i:,.2f}"); st.rerun()
            else: st.warning("⚠️ Informe ao menos um salário.")
        df_rec=df[df["Tipo"]=="Entrada"].drop(columns=["_dt"],errors="ignore").sort_values("Data",ascending=False)
        if not df_rec.empty:
            st.markdown("<br>",unsafe_allow_html=True)
            tabela_com_excluir(df_rec, key_prefix="rec")
            r1,r2,r3=st.columns(3); r1.metric("Total",f"R$ {df_rec['Valor'].sum():,.2f}"); r2.metric("Octavio",f"R$ {df_rec[df_rec['Pessoa']=='Octavio']['Valor'].sum():,.2f}"); r3.metric("Isabela",f"R$ {df_rec[df_rec['Pessoa']=='Isabela']['Valor'].sum():,.2f}")
    with sr[1]:
        with st.form("form_rv",clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1: drv=st.date_input("📅 Data",value=hoje); prv=st.selectbox("👤 Pessoa",pessoas)
            with c2: dscv=st.text_input("📝 Descrição"); valv=st.number_input("💰 Valor",min_value=0.0,format="%.2f")
            crv_r=st.selectbox("🏷️ Tipo",opts_ui(receita=True)); crv=limpa(crv_r); obsv=st.text_area("📋 Obs (opcional)",height=55)
            if st.form_submit_button("💾 Lançar",use_container_width=True):
                if dscv and valv>0 and crv: inserir([[str(drv),prv,crv,f"{dscv} — {obsv}" if obsv else dscv,valv,"Entrada"]]); st.success(f"✅ R$ {valv:,.2f}"); st.rerun()
                else: st.warning("⚠️ Preencha todos os campos.")

# ══════════════════════════════════════════
# TAB 4 — OFX + IA + CONCILIAÇÃO BANCÁRIA
# ══════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">🏦 Importação OFX com Conciliação Bancária</div>',unsafe_allow_html=True)
    st.markdown("""<div style="background:var(--accent-dim);border:1px solid rgba(41,217,245,.22);
        border-radius:12px;padding:.9rem 1.2rem;margin-bottom:1.2rem;">
        <b style="color:var(--accent);">Conciliação inteligente:</b>
        <span style="color:var(--text-sec);font-size:.86rem;">
        ✅ <b>Match</b> — bate com lançamento manual → mantém seu nome e categoria &nbsp;|&nbsp;
        ≈ <b>Similar</b> — parecido → você confirma &nbsp;|&nbsp;
        🔴 <b>Novo</b> — categoriza com IA &nbsp;|&nbsp;
        ⊗ <b>Duplicado</b> → ignora automaticamente
        </span>
    </div>""", unsafe_allow_html=True)

    file=st.file_uploader("📂 Arquivo OFX",type="ofx")
    if file:
        fl=fixos.to_dict("records") if not fixos.empty else []
        with st.spinner("🔄 Lendo extrato e conciliando com lançamentos manuais..."):
            ofx=OfxParser.parse(io.BytesIO(file.read()))
            transacoes_brutas=[]
            for t in ofx.account.statement.transactions:
                desc  = t.memo or t.payee or "Sem descrição"
                data  = t.date.strftime("%Y-%m-%d")
                valor = abs(float(t.amount))
                tipo  = "Entrada" if t.amount>0 else "Saída"
                transacoes_brutas.append({"Data":data,"Descricao":desc,"Valor":valor,"Tipo":tipo})

            # Roda motor de conciliação (passa fixos para bloquear)
            conciliadas = conciliar_extrato(transacoes_brutas, df, fixos)

        if not conciliadas:
            st.info("✅ Nenhuma transação nova no extrato!")
        else:
            # Contadores por status
            n_match    = sum(1 for t in conciliadas if t["_status"]=="match")
            n_similar  = sum(1 for t in conciliadas if t["_status"]=="similar")
            n_novo     = sum(1 for t in conciliadas if t["_status"]=="novo")
            n_dup      = sum(1 for t in conciliadas if t["_status"]=="duplicado")
            n_fixo     = sum(1 for t in conciliadas if t["_status"]=="fixo")
            tt         = len(conciliadas)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("📦 Total extrato", tt)
            c2.metric("✅ Match manual",  n_match)
            c3.metric("≈ Similar",        n_similar)
            c4.metric("🔴 Novo",           n_novo)
            c5.metric("🔁 Fixo — bloq.",  n_fixo)
            c6.metric("⊗ Duplicado",      n_dup)

            st.markdown("<br>",unsafe_allow_html=True)

            if "ofx_cats" not in st.session_state: st.session_state.ofx_cats={}
            if "ofx_nomes" not in st.session_state: st.session_state.ofx_nomes={}

            # Inicializa com dados do match manual
            for i,tx in enumerate(conciliadas):
                if i not in st.session_state.ofx_cats:
                    if tx["_status"] in ("match","fixo"):
                        st.session_state.ofx_cats[i]  = tx.get("_categoria_manual","")
                        st.session_state.ofx_nomes[i] = tx.get("_nome_manual", tx["Descricao"])
                    elif tx["_status"] in ("duplicado",):
                        st.session_state.ofx_cats[i]  = "__duplicado__"
                        st.session_state.ofx_nomes[i] = tx["Descricao"]
                    else:
                        cat_ia,_ = sugerir(tx["Descricao"])
                        st.session_state.ofx_cats[i]  = cat_ia or ""
                        st.session_state.ofx_nomes[i] = tx["Descricao"]

            # ── FIXOS BLOQUEADOS ──
            fixo_txs = [(i,tx) for i,tx in enumerate(conciliadas) if tx["_status"]=="fixo"]
            if fixo_txs:
                with st.expander(f"🔁 {len(fixo_txs)} despesa(s) fixa(s) — não serão importadas (já lançadas como fixo)"):
                    for i,tx in fixo_txs:
                        st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;
                            padding:.5rem .75rem;margin:.2rem 0;background:var(--surface);
                            border-radius:8px;border-left:3px solid var(--yellow);">
                            <span style="font-size:.82rem;">🔁 {tx["Descricao"]}</span>
                            <span style="font-size:.78rem;color:var(--yellow);">
                                R$ {tx["Valor"]:,.2f} · Fixo: <b>{tx.get("_fixo_nome","")}</b>
                                · Cat: {tx.get("_fixo_cat","")}
                            </span>
                        </div>""", unsafe_allow_html=True)

            # ── MATCH PERFEITO ──
            match_txs = [(i,tx) for i,tx in enumerate(conciliadas) if tx["_status"]=="match"]
            if match_txs:
                st.markdown('<div class="section-title">✅ Match com Lançamentos Manuais</div>',unsafe_allow_html=True)
                for i,tx in match_txs:
                    man = tx.get("_manual",{})
                    st.markdown(f"""<div class="alert-card ok">
                        <div class="alert-icon">✅</div>
                        <div style="flex:1;">
                            <div class="alert-title">{tx.get("_nome_manual", tx["Descricao"])}</div>
                            <div class="alert-msg">
                                Extrato: <i>{tx["Descricao"]}</i> &nbsp;·&nbsp;
                                R$ {tx["Valor"]:,.2f} &nbsp;·&nbsp; {tx["Data"]} &nbsp;·&nbsp;
                                Categoria: <b>{tx.get("_categoria_manual","")}</b>
                                <span class="badge green">Manual prevalece</span>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

            # ── SIMILAR — precisa confirmar ──
            sim_txs = [(i,tx) for i,tx in enumerate(conciliadas) if tx["_status"]=="similar"]
            if sim_txs:
                st.markdown('<div class="section-title">≈ Similares — Confirme se é o mesmo</div>',unsafe_allow_html=True)
                for i,tx in sim_txs:
                    man = tx.get("_manual",{})
                    nome_man = tx.get("_nome_manual","")
                    cat_man  = tx.get("_categoria_manual","")
                    st.markdown(f"""<div class="alert-card warn">
                        <div class="alert-icon">≈</div>
                        <div style="flex:1;">
                            <div class="alert-title">Extrato: {tx["Descricao"]}</div>
                            <div class="alert-msg">R$ {tx["Valor"]:,.2f} · {tx["Data"]} &nbsp;|&nbsp;
                            Manual encontrado: <b>{nome_man}</b> → Categoria: <b>{cat_man}</b></div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    sc1,sc2 = st.columns(2)
                    if sc1.button(f"✅ Sim, é '{nome_man}'", key=f"sim_ok_{i}"):
                        st.session_state.ofx_cats[i]  = cat_man
                        st.session_state.ofx_nomes[i] = nome_man
                        st.rerun()
                    if sc2.button("❌ Não, é diferente", key=f"sim_no_{i}"):
                        st.session_state[f"sim_manual_{i}"] = True
                    if st.session_state.get(f"sim_manual_{i}"):
                        cm1,cm2 = st.columns([2,2])
                        with cm1:
                            novo_nome = st.text_input("📝 Nome correto", value=tx["Descricao"], key=f"sim_nome_{i}")
                        with cm2:
                            nova_cat = st.selectbox("🏷️ Categoria", cat_desp, key=f"sim_cat_{i}")
                        if st.button("💾 Confirmar", key=f"sim_conf_{i}"):
                            st.session_state.ofx_cats[i]  = nova_cat
                            st.session_state.ofx_nomes[i] = novo_nome
                            salvar_regra(tx["Descricao"], nova_cat)
                            st.session_state[f"sim_manual_{i}"] = False
                            st.rerun()

            # ── NOVO — categorizar com IA ──
            novo_txs = [(i,tx) for i,tx in enumerate(conciliadas) if tx["_status"]=="novo"]
            if novo_txs:
                st.markdown('<div class="section-title">🔴 Novos — Sem correspondência manual</div>',unsafe_allow_html=True)
                for i,tx in novo_txs:
                    cat_atual = st.session_state.ofx_cats.get(i,"")
                    st.markdown(f"""<div class="ai-card">
                        <div class="ai-desc">💳 {tx["Descricao"]}</div>
                        <div class="ai-meta">📅 {tx["Data"]} &nbsp;|&nbsp; 💰 R$ {tx["Valor"]:,.2f}
                        &nbsp;|&nbsp; {"🟢 Entrada" if tx["Tipo"]=="Entrada" else "🔴 Saída"}</div>
                    </div>""", unsafe_allow_html=True)
                    cn1,cn2,cn3 = st.columns([2,2,1])
                    with cn1:
                        novo_nome_n = st.text_input("📝 Nome (opcional)", value=tx["Descricao"], key=f"novo_nome_{i}")
                    with cn2:
                        idx_cat = cat_desp.index(cat_atual) if cat_atual in cat_desp else 0
                        nova_cat_n = st.selectbox("🏷️ Categoria", cat_desp, index=idx_cat, key=f"novo_cat_{i}")
                    with cn3:
                        st.markdown("<br>",unsafe_allow_html=True)
                        if st.button("💾", key=f"novo_save_{i}"):
                            salvar_regra(tx["Descricao"], nova_cat_n)
                            st.session_state.ofx_cats[i]  = nova_cat_n
                            st.session_state.ofx_nomes[i] = novo_nome_n
                            st.rerun()

            # ── DUPLICADOS ──
            dup_txs = [(i,tx) for i,tx in enumerate(conciliadas) if tx["_status"]=="duplicado"]
            if dup_txs:
                with st.expander(f"⊗ {len(dup_txs)} duplicado(s) ignorado(s) — clique para ver"):
                    for i,tx in dup_txs:
                        st.markdown(f'<div style="font-size:.8rem;color:var(--muted);padding:.25rem 0;">⊗ {tx["Descricao"]} · R$ {tx["Valor"]:,.2f} · {tx["Data"]}</div>',unsafe_allow_html=True)

            # ── PREVIEW FINAL ──
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown('<div class="section-title">📋 Preview Final para Importação</div>',unsafe_allow_html=True)

            rows_prev = []
            for i,tx in enumerate(conciliadas):
                if tx["_status"]=="duplicado": continue
                cat  = st.session_state.ofx_cats.get(i,"")
                nome = st.session_state.ofx_nomes.get(i, tx["Descricao"])
                rows_prev.append({
                    "Data":      tx["Data"],
                    "Nome":      nome,
                    "Valor":     f"R$ {tx['Valor']:,.2f}",
                    "Tipo":      tx["Tipo"],
                    "Categoria": cat or "⏳",
                    "Origem":    "📋 Manual" if tx["_status"]=="match" else "🤖 IA",
                    "Status":    "✅" if (cat and cat!="__duplicado__") else "⏳"
                })
            if rows_prev:
                st.dataframe(pd.DataFrame(rows_prev), use_container_width=True, hide_index=True)

            # Verifica pendentes
            pendentes_imp = [
                i for i,tx in enumerate(conciliadas)
                if tx["_status"]!="duplicado"
                and (not st.session_state.ofx_cats.get(i) or st.session_state.ofx_cats.get(i)=="__duplicado__")
            ]
            prontos_imp = len(rows_prev) - len(pendentes_imp)

            if pendentes_imp:
                st.warning(f"⚠️ {len(pendentes_imp)} transação(ões) ainda sem categoria.")

            if st.button(f"🚀 Importar {prontos_imp} lançamentos conciliados",
                         disabled=bool(pendentes_imp), use_container_width=True):
                lns=[]
                for i,tx in enumerate(conciliadas):
                    if tx["_status"]=="duplicado": continue
                    cat  = st.session_state.ofx_cats.get(i,"")
                    nome = st.session_state.ofx_nomes.get(i, tx["Descricao"])
                    if not cat or cat=="__duplicado__": continue
                    pessoa = tx.get("_pessoa_manual", "Octavio")
                    lns.append([tx["Data"], pessoa, cat, nome, tx["Valor"], tx["Tipo"]])
                inserir(lns)
                st.session_state.ofx_cats  = {}
                st.session_state.ofx_nomes = {}
                st.success(f"✅ {len(lns)} lançamentos importados com conciliação bancária! 🏦")
                st.rerun()

# ══════════════════════════════════════════
# TAB 5 — PDF
# ══════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-title">📄 Importação PDF</div>',unsafe_allow_html=True)
    pdf=st.file_uploader("📂 PDF",type="pdf")
    if pdf:
        with st.spinner("Extraindo..."):
            dados=[]
            with pdfplumber.open(pdf) as p:
                for pg in p.pages:
                    tx=pg.extract_text()
                    if tx:
                        for linha in tx.split("\n"):
                            pts=linha.split()
                            if len(pts)>=3:
                                try: v=float(pts[-1].replace(",",".")); dados.append([pts[0]," ".join(pts[1:-1]),v])
                                except: pass
        if dados: df_pdf=pd.DataFrame(dados,columns=["Data","Descrição","Valor"]); st.success(f"✅ {len(df_pdf)} linhas"); st.dataframe(df_pdf,use_container_width=True,hide_index=True)
        else: st.warning("⚠️ Nenhum dado encontrado.")

# ══════════════════════════════════════════
# TAB 6 — CSV
# ══════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="section-title">📥 Importação CSV</div>',unsafe_allow_html=True)
    st.markdown('<div style="background:var(--yellow-dim);border:1px solid rgba(251,191,36,.22);border-radius:12px;padding:.9rem 1.2rem;margin-bottom:1.2rem;"><b style="color:var(--yellow);">Bancos:</b> <span style="color:var(--text-sec);font-size:.86rem;">Itaú · Bradesco · Nubank · XP · Inter — exportam CSV direto.</span></div>',unsafe_allow_html=True)
    csv_f=st.file_uploader("📂 CSV / TXT",type=["csv","txt"])
    if csv_f:
        dfc=None
        for sep in [";",",","\t"]:
            for enc in ["utf-8","latin-1","cp1252"]:
                try:
                    csv_f.seek(0); t=pd.read_csv(csv_f,sep=sep,encoding=enc,on_bad_lines="skip")
                    if len(t.columns)>=2: dfc=t; break
                except: pass
            if dfc is not None: break
        if dfc is None: st.error("❌ Formato não reconhecido.")
        else:
            st.dataframe(dfc.head(6),use_container_width=True,hide_index=True)
            cols=["(ignorar)"]+list(dfc.columns)
            c1,c2,c3,c4=st.columns(4)
            cd=c1.selectbox("📅 DATA",cols,key="cd"); ce=c2.selectbox("📝 DESCRIÇÃO",cols,key="ce"); cv=c3.selectbox("💰 VALOR",cols,key="cv"); ct=c4.selectbox("↕️ TIPO",cols,key="ct")
            pc=st.selectbox("👤 Pessoa",pessoas,key="cp"); tp=st.selectbox("↕️ Tipo padrão",["Saída","Entrada"],key="ctp")
            if st.button("🔍 Pré-visualizar"):
                if "(ignorar)" in [cd,ce,cv]: st.warning("⚠️ Mapeie Data, Descrição e Valor.")
                else:
                    lns=[]
                    for _,r in dfc.iterrows():
                        try:
                            v=abs(float(str(r[cv]).replace("R$","").replace(".","").replace(",",".").strip()))
                            ti=tp if ct=="(ignorar)" else ("Entrada" if "cred" in str(r[ct]).lower() else "Saída")
                            cat,_=sugerir(str(r[ce]))
                            lns.append({"Data":str(r[cd]),"Descrição":str(r[ce]),"Valor":v,"Tipo":ti,"Categoria IA":cat or "⏳"})
                        except: pass
                    st.session_state["csv_pv"]=(pd.DataFrame(lns),pc); st.dataframe(pd.DataFrame(lns),use_container_width=True,hide_index=True)
            if "csv_pv" in st.session_state:
                dpv,pcs=st.session_state["csv_pv"]
                if st.button("🚀 Importar CSV",use_container_width=True):
                    lns2=[[r["Data"],pcs,r["Categoria IA"] if r["Categoria IA"]!="⏳" else "Outros",r["Descrição"],r["Valor"],r["Tipo"]] for _,r in dpv.iterrows()]
                    inserir(lns2); del st.session_state["csv_pv"]; st.success(f"✅ {len(lns2)} importados!"); st.rerun()

# ══════════════════════════════════════════
# TAB 7 — FIXOS
# ══════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-title">⚙️ Despesas Fixas</div>',unsafe_allow_html=True)
    st.markdown('<div style="background:var(--yellow-dim);border:1px solid rgba(251,191,36,.22);border-radius:12px;padding:.9rem 1.2rem;margin-bottom:1.2rem;"><b style="color:var(--yellow);">Fixos aqui são detectados automaticamente no OFX</b> <span style="color:var(--text-sec);font-size:.86rem;">e lançados sem interação. O dia de vencimento aparece no calendário.</span></div>',unsafe_allow_html=True)
    cl2,cr2=st.columns([2,1])
    with cl2:
        if fixos.empty: st.info("Nenhum fixo cadastrado.")
        else: st.dataframe(fixos.drop(columns=["ID"],errors="ignore"),use_container_width=True,hide_index=True)
    with cr2:
        with st.form("ff",clear_on_submit=True):
            st.markdown("**➕ Novo Fixo**")
            dfx=st.text_input("Descrição"); ofx2=opts_ui(despesa=True); cfx_r=st.selectbox("Categoria",ofx2,key="cfx"); cfx=limpa(cfx_r)
            vfx=st.number_input("Valor",min_value=0.0,format="%.2f"); pfx=st.selectbox("Pessoa",pessoas); dfxd=st.number_input("Dia venc.",min_value=1,max_value=31,value=5)
            if st.form_submit_button("💾 Salvar",use_container_width=True):
                if dfx and cfx and vfx>0: ws["fixos"].append_row([dfx,cfx,vfx,pfx,dfxd]); load_fixos.clear(); st.success(f"✅ '{dfx}' cadastrado!"); st.rerun()
                else: st.warning("⚠️ Preencha tudo.")
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("⚡ Lançar TODOS agora",use_container_width=True):
            if fixos.empty: st.warning("Sem fixos.")
            else:
                lns=[]; dt=datetime.today().strftime("%Y-%m-01")
                for _,r in fixos.iterrows(): lns.append([dt,r.get("Pessoa",""),r.get("Categoria",""),r.get("Descricao",""),r.get("Valor",0),"Saída"])
                inserir(lns); st.success(f"✅ {len(lns)} fixos lançados!")

# ══════════════════════════════════════════
# TAB 8 — PARCELAS
# ══════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-title">💳 Controle de Parcelas</div>',unsafe_allow_html=True)
    sp=st.tabs(["➕ Nova Compra Parcelada","📋 Em Andamento"])
    with sp[0]:
        with st.form("fp",clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1: dsp=st.text_input("📝 Descrição"); op=opts_ui(despesa=True); cpr=st.selectbox("🏷️ Categoria",op,key="cp2"); cpp=limpa(cpr); pep=st.selectbox("👤 Pessoa",pessoas)
            with c2:
                totp=st.number_input("💰 Valor total",min_value=0.0,format="%.2f"); np=st.number_input("🔢 Parcelas",min_value=1,step=1,value=1)
                vp=totp/max(int(np),1)
                st.markdown(f'<div style="background:var(--accent-dim);border-radius:9px;padding:.75rem 1rem;border:1px solid rgba(41,217,245,.15);"><span style="color:var(--muted);font-size:.76rem;">POR PARCELA</span><br><span style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:var(--accent);">R$ {vp:,.2f}</span></div>',unsafe_allow_html=True)
            if st.form_submit_button("📆 Gerar",use_container_width=True):
                if dsp and totp>0 and cpp:
                    lns=[]; v2=totp/int(np); m=datetime.today()
                    for i in range(int(np)):
                        mo=(m.month+i-1)%12+1; yr=m.year+(m.month+i-1)//12; dt=datetime(yr,mo,1)
                        lns.append([str(dt.date()),pep,cpp,f"{dsp} ({i+1}/{int(np)})",v2,"Saída"])
                    inserir(lns); ws["parcelas"].append_row([dsp,cpp,v2,int(np),1,pep,str(datetime.today().date())]); st.success(f"✅ {int(np)}x R$ {v2:,.2f}"); st.rerun()
                else: st.warning("⚠️ Preencha todos os campos.")
    with sp[1]:
        pa2=load_parcelas()
        if pa2.empty: st.info("Nenhuma parcela.")
        else:
            for _,p in pa2.iterrows():
                try:
                    at=int(p.get("ParcelaAtual",0)); tot=int(p.get("TotalParcelas",1)); pp=at/tot*100; rest=tot-at; val=float(p.get("Valor",0))
                    pc3="#22d3a0" if pp<70 else "#fbbf24" if pp<90 else "#f8625a"
                    st.markdown(f'<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem 1.25rem;margin:.4rem 0;"><div style="display:flex;justify-content:space-between;margin-bottom:.5rem;"><span style="font-weight:600;">💳 {p.get("Descricao","")}</span><span class="badge {"green" if rest<=1 else "blue"}">{at}/{tot}</span></div><div class="prog-bar"><div class="prog-fill" style="width:{pp:.0f}%;background:{pc3};"></div></div><div style="display:flex;justify-content:space-between;margin-top:.4rem;font-size:.78rem;color:var(--muted);"><span>R$ {val:,.2f}/parc · R$ {val*rest:,.2f} restante</span><span>{rest} a vencer</span></div></div>',unsafe_allow_html=True)
                except: pass

# ══════════════════════════════════════════
# TAB 9 — METAS
# ══════════════════════════════════════════
with tabs[9]:
    st.markdown('<div class="section-title">🎯 Metas Mensais de Gasto</div>', unsafe_allow_html=True)
    st.markdown("""<div style="background:var(--accent-dim);border:1px solid rgba(41,217,245,.22);
        border-radius:12px;padding:.9rem 1.2rem;margin-bottom:1.2rem;">
        <b style="color:var(--accent);">Como funciona:</b>
        <span style="color:var(--text-sec);font-size:.86rem;"> Defina um teto de gasto por categoria.
        Quando atingir 80% do limite, aparece alerta no Painel Geral automaticamente.</span>
    </div>""", unsafe_allow_html=True)

    # Seletor de mês/ano
    cm1,cm2 = st.columns(2)
    mes_meta = cm1.selectbox("📅 Mês", list(range(1,13)),
        index=hoje.month-1, format_func=lambda x: MESES_PT[x-1], key="meta_mes")
    ano_meta = cm2.number_input("📅 Ano", min_value=2020, max_value=2030,
        value=hoje.year, step=1, key="meta_ano")

    st.markdown("<br>", unsafe_allow_html=True)

    # Categorias sugeridas + todas as despesas
    cats_meta = [
        "Supermercado / Feira", "Restaurante / Delivery",
        "Combustível", "Lazer / Passeios Família",
        "Roupas / Calçados / Acessórios", "Farmácia",
        "Padaria / Café", "Lanche / Fast Food",
        "Barbearia / Beleza / Estética", "Eletrônicos / Tecnologia",
    ] + [c for c in cat_desp if c not in [
        "Supermercado / Feira","Restaurante / Delivery","Combustível",
        "Lazer / Passeios Família","Roupas / Calçados / Acessórios","Farmácia",
        "Padaria / Café","Lanche / Fast Food","Barbearia / Beleza / Estética",
        "Eletrônicos / Tecnologia"]]

    metas_atuais = get_metas_mes(mes_meta, ano_meta)

    st.markdown('<div class="section-title">💰 Definir Metas</div>', unsafe_allow_html=True)

    # Gasto real do mês selecionado para mostrar contexto
    df_meta_mes = df.copy()
    df_meta_mes["_dt"] = pd.to_datetime(df_meta_mes["Data"], errors="coerce")
    dm_meta = df_meta_mes[
        (df_meta_mes["_dt"].dt.month==mes_meta) &
        (df_meta_mes["_dt"].dt.year==ano_meta) &
        (df_meta_mes["Tipo"]=="Saída")
    ]

    for cat in cats_meta:
        val_atual = metas_atuais.get(cat, 0.0)
        gasto_real = dm_meta[dm_meta["Categoria"]==cat]["Valor"].sum()

        c1,c2,c3,c4 = st.columns([3,2,2,1])
        c1.markdown(f'<div style="font-size:.84rem;padding:.5rem 0;">{cat}</div>',
                   unsafe_allow_html=True)
        nova_meta = c2.number_input(
            "Meta (R$)", min_value=0.0, value=float(val_atual),
            format="%.2f", key=f"meta_{cat}", label_visibility="collapsed"
        )
        pct_m = (gasto_real/nova_meta*100) if nova_meta>0 else 0
        cor_m = "#22d3a0" if pct_m<80 else "#fbbf24" if pct_m<100 else "#f8625a"
        c3.markdown(f'<div style="font-size:.78rem;color:{cor_m};padding:.5rem 0;">Gasto: R$ {gasto_real:,.2f} ({pct_m:.0f}%)</div>',
                   unsafe_allow_html=True)
        if c4.button("💾", key=f"save_meta_{cat}"):
            if nova_meta > 0:
                salvar_meta(cat, nova_meta, mes_meta, ano_meta)
                st.success(f"✅ Meta de R$ {nova_meta:,.2f} salva para {cat}!")
                st.rerun()

    # Resumo das metas
    if metas_atuais:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">📊 Resumo — {MESES_PT[mes_meta-1]}/{ano_meta}</div>',
                   unsafe_allow_html=True)
        total_meta  = sum(metas_atuais.values())
        total_gasto = sum(dm_meta[dm_meta["Categoria"]==c]["Valor"].sum()
                         for c in metas_atuais.keys())
        m1,m2,m3 = st.columns(3)
        m1.metric("🎯 Total orçado", f"R$ {total_meta:,.2f}")
        m2.metric("💸 Total gasto",  f"R$ {total_gasto:,.2f}")
        m3.metric("💰 Disponível",   f"R$ {total_meta-total_gasto:,.2f}")

# ══════════════════════════════════════════
# TAB 10 — PROJEÇÃO DE FLUXO DE CAIXA
# ══════════════════════════════════════════
with tabs[10]:
    st.markdown('<div class="section-title">📈 Projeção de Fluxo de Caixa — Próximos 3 Meses</div>',
               unsafe_allow_html=True)
    st.markdown("""<div style="background:var(--accent2-dim);border:1px solid rgba(139,92,246,.22);
        border-radius:12px;padding:.9rem 1.2rem;margin-bottom:1.2rem;">
        <b style="color:var(--accent2);">Como a IA projeta:</b>
        <span style="color:var(--text-sec);font-size:.86rem;">
        Média dos últimos 3 meses de receita e despesa variável +
        fixos recorrentes cadastrados + parcelas ativas no período.</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("🤖 Calculando projeção..."):
        proj = projetar_fluxo(df, fixos, parcelas, meses_ahead=3)

    if not proj:
        st.info("Dados insuficientes para projeção. Adicione mais lançamentos.")
    else:
        # KPIs de projeção
        p1,p2,p3 = st.columns(3)
        for col,p in zip([p1,p2,p3], proj):
            saldo_cor = "var(--green)" if p["saldo_acum"]>=0 else "var(--red)"
            col.markdown(f"""<div class="kpi-card {'blue' if p['saldo_acum']>=0 else 'red'}">
                <div class="kpi-label">📅 {p['label']}</div>
                <div class="kpi-value" style="font-size:1.3rem;">R$ {p['saldo_acum']:,.0f}</div>
                <div class="kpi-sub">Saldo acumulado projetado</div>
                <div style="margin-top:.5rem;font-size:.75rem;color:var(--text-sec);">
                    Receita: R$ {p['receita']:,.0f}<br>
                    Despesa: R$ {p['despesa']:,.0f}
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Gráfico de barras empilhadas
        st.markdown('<div class="section-title">📊 Composição das Despesas Projetadas</div>',
                   unsafe_allow_html=True)
        labels_p = [p["label"] for p in proj]
        fig_proj = go.Figure()
        fig_proj.add_trace(go.Bar(
            name="Variável (histórico)", x=labels_p,
            y=[p["variavel"] for p in proj],
            marker_color="#f8625a", opacity=0.85
        ))
        fig_proj.add_trace(go.Bar(
            name="Fixos recorrentes", x=labels_p,
            y=[p["fixos"] for p in proj],
            marker_color="#fbbf24", opacity=0.85
        ))
        fig_proj.add_trace(go.Bar(
            name="Parcelas ativas", x=labels_p,
            y=[p["parcelas"] for p in proj],
            marker_color="#8b5cf6", opacity=0.85
        ))
        fig_proj.add_trace(go.Scatter(
            name="Receita projetada", x=labels_p,
            y=[p["receita"] for p in proj],
            mode="lines+markers",
            line=dict(color="#22d3a0", width=3),
            marker=dict(size=10)
        ))
        fig_proj.update_layout(
            barmode="stack",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#b8c5e0",
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2),
            xaxis=dict(gridcolor="#2a3a5c"),
            yaxis=dict(gridcolor="#2a3a5c", title="R$"),
            margin=dict(t=10, b=10, l=0, r=0),
            hovermode="x unified"
        )
        st.plotly_chart(fig_proj, use_container_width=True)

        # Tabela detalhada
        st.markdown('<div class="section-title">📋 Detalhamento da Projeção</div>',
                   unsafe_allow_html=True)
        df_proj = pd.DataFrame([{
            "Mês":              p["label"],
            "Receita proj.":    f"R$ {p['receita']:,.2f}",
            "Despesa variável": f"R$ {p['variavel']:,.2f}",
            "Fixos":            f"R$ {p['fixos']:,.2f}",
            "Parcelas":         f"R$ {p['parcelas']:,.2f}",
            "Total despesa":    f"R$ {p['despesa']:,.2f}",
            "Saldo acum.":      f"R$ {p['saldo_acum']:,.2f}",
        } for p in proj])
        st.dataframe(df_proj, use_container_width=True, hide_index=True)

        st.markdown("""<div style="background:var(--yellow-dim);border:1px solid rgba(251,191,36,.2);
            border-radius:10px;padding:.75rem 1rem;margin-top:.5rem;font-size:.8rem;color:var(--muted);">
            ⚠️ <b style="color:var(--yellow);">Atenção:</b>
            Projeção baseada em médias históricas. Receitas e despesas reais podem variar.
            Quanto mais lançamentos você tiver, mais precisa fica a projeção.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 11 — INVESTIMENTOS
# ══════════════════════════════════════════
with tabs[11]:
    st.markdown('<div class="section-title">💹 Simulador de Investimentos</div>',unsafe_allow_html=True)
    cc2,cg2=st.columns([1,2])
    with cc2:
        vi=st.number_input("💰 Capital inicial",value=1000.0,format="%.2f"); ap=st.number_input("📅 Aporte mensal",value=500.0,format="%.2f")
        anos=st.slider("⏳ Período (anos)",1,40,10); txa=st.slider("📊 Taxa anual %",1.0,30.0,12.0,.5)
        tam=(1+txa/100)**(1/12)-1; tot=vi; vals=[]; aps=[]; apt=vi
        for _ in range(anos*12): tot=tot*(1+tam)+ap; apt+=ap; vals.append(tot); aps.append(apt)
        rend=tot-apt
        st.markdown(f'<div style="background:var(--green-dim);border:1px solid rgba(34,211,160,.22);border-radius:12px;padding:1rem 1.2rem;margin-top:.8rem;"><div style="font-size:.72rem;color:var(--muted);text-transform:uppercase;">Montante Final</div><div style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:var(--green);">R$ {tot:,.2f}</div><div style="font-size:.8rem;color:var(--text-sec);margin-top:.25rem;">Rendimento: <b>R$ {rend:,.2f}</b><br>Aportado: R$ {apt:,.2f}</div></div>',unsafe_allow_html=True)
    with cg2:
        dfi=pd.DataFrame({"Mês":range(anos*12),"Patrimônio":vals,"Aportado":aps})
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=dfi["Mês"],y=dfi["Patrimônio"],fill="tozeroy",name="Patrimônio",line=dict(color="#29d9f5",width=2.5),fillcolor="rgba(41,217,245,.1)"))
        fig.add_trace(go.Scatter(x=dfi["Mês"],y=dfi["Aportado"],fill="tozeroy",name="Aportado",line=dict(color="#8b5cf6",width=2,dash="dot"),fillcolor="rgba(139,92,246,.08)"))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",legend=dict(bgcolor="rgba(0,0,0,0)"),xaxis=dict(gridcolor="#2a3a5c",title="Meses"),yaxis=dict(gridcolor="#2a3a5c",title="R$"),margin=dict(t=10,b=10,l=0,r=0),hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)

# ══════════════════════════════════════════
# TAB 12 — PATRIMÔNIO
# ══════════════════════════════════════════
with tabs[12]:
    st.markdown('<div class="section-title">🏛️ Balanço Patrimonial</div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    bv=c1.number_input("🏠 Bens",min_value=0.0,format="%.2f"); iv=c2.number_input("📈 Investimentos",min_value=0.0,format="%.2f"); dv=c3.number_input("💸 Dívidas",min_value=0.0,format="%.2f")
    pat=bv+iv-dv; cp="#22d3a0" if pat>=0 else "#f8625a"
    st.markdown(f'<div style="margin:1.5rem 0;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:2rem;text-align:center;"><div style="font-size:.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:.5rem;">Patrimônio Líquido</div><div style="font-family:Syne,sans-serif;font-size:3rem;font-weight:800;color:{cp};">R$ {pat:,.2f}</div><div style="color:var(--muted);font-size:.86rem;margin-top:.5rem;">Bens R$ {bv:,.2f} + Inv R$ {iv:,.2f} − Dívidas R$ {dv:,.2f}</div></div>',unsafe_allow_html=True)
    if bv+iv>0:
        fig=go.Figure(go.Waterfall(orientation="v",measure=["relative","relative","relative","total"],x=["Bens","Investimentos","−Dívidas","Patrimônio"],y=[bv,iv,-dv,0],connector={"line":{"color":"#2a3a5c"}},increasing={"marker":{"color":"#22d3a0"}},decreasing={"marker":{"color":"#f8625a"}},totals={"marker":{"color":"#29d9f5"}}))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#b8c5e0",margin=dict(t=5,b=5,l=0,r=0))
        st.plotly_chart(fig,use_container_width=True)

# ══════════════════════════════════════════
# TAB 13 — BENS
# ══════════════════════════════════════════
with tabs[13]:
    st.markdown('<div class="section-title">📦 Cadastro de Bens</div>',unsafe_allow_html=True)
    cf2,cl2=st.columns([1,2])
    with cf2:
        with st.form("fb",clear_on_submit=True):
            db=st.text_input("📝 Descrição"); tb=st.selectbox("🏷️ Tipo",["Imóvel","Veículo","Investimento","Outro"])
            vb=st.number_input("💰 Valor",min_value=0.0,format="%.2f"); dob=st.selectbox("👤 Proprietário",pessoas+["Ambos"])
            if st.form_submit_button("💾 Cadastrar",use_container_width=True):
                if db: ws["bens"].append_row([db,tb,vb,dob]); st.success(f"✅ {db}!"); st.rerun()
                else: st.warning("⚠️ Informe a descrição.")
    with cl2:
        dfb=load(ws["bens"])
        if dfb.empty: st.info("Nenhum bem.")
        else:
            st.dataframe(dfb.drop(columns=["ID"],errors="ignore"),use_container_width=True,hide_index=True)
            tot=pd.to_numeric(dfb.get("Valor",pd.Series([])),errors="coerce").sum()
            st.markdown(f'<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem 1.5rem;margin-top:1rem;display:flex;justify-content:space-between;align-items:center;"><span style="color:var(--muted);font-size:.84rem;">Total em Bens</span><span style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:var(--accent);">R$ {tot:,.2f}</span></div>',unsafe_allow_html=True)
if __name__ == "__main__":
    pass