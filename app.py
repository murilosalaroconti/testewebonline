# app.py - Versão Streamlit do sistema do Murilo
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt
from PIL import Image
import io
import numpy as np
import matplotlib.patches as mpatches
import altair as alt
from pathlib import Path
from google.oauth2.service_account import Credentials
import gspread
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import cm
import tempfile
import os
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle
)


BASE_DIR = Path(__file__).parent
IMAGE_PATH = BASE_DIR / "imagens" / "bernardo1.jpeg"

st.set_page_config(page_title="Registro Atleta - Web", layout="wide", initial_sidebar_state="expanded")

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "home"


# ----------------------
# Configurações de arquivos
# ----------------------
EXPECTED_REGISTROS_COLUMNS = [
    "Casa", "Visitante", "Data", "Horário", "Campeonato", "Quadro Jogado",
    "Minutos Jogados", "Gols Marcados", "Assistências",
    "Chutes","Chutes Errados", "Desarmes", "Passes-chave","Passes Errados", "Faltas Sofridas", "Participações Indiretas",
    "Resultado", "Local", "Condição do Campo",
    "Treino", "Date", "Hora"
]

EXPECTED_SAUDE_COLUMNS = [
    "Data",
    "Alimentação",
    "Hidratação",
    "Cansaço",
    "Observação"
]


# --- NOVOS CAMINHOS PARA LOGOS (Crie os arquivos nesta pasta) ---
LOGO_PATH_1 = BASE_DIR / "logos" / "paulista.png"
LOGO_PATH_2 = BASE_DIR / "logos" / "ligapta.png"
LOGO_PATH_3 = BASE_DIR / "logos" / "gru.png"
LOGO_PATH_4 = BASE_DIR / "logos" / "paulistacup.png"
LOGO_PATH_5 = BASE_DIR / "logos" / "juventude.png"
LOGO_PATH_6 = BASE_DIR / "logos" / "apf.png"
LOGO_PATH_7 = BASE_DIR / "logos" / "nike.png"
LOGO_PATH_8 = BASE_DIR / "logos" / "cuebla.png"

#URLS DOS CAMPEONATOS
CAMPEONATO_URLS = {
    "paulista.png": "https://eventos.admfutsal.com.br/evento/873/jogos",
    "ligapta.png": "https://ligapaulistafutsal.com.br/evento/178/liga-paulista-de-futsal-sub-09-2025",
    "gru.png": "https://copafacil.com/-vpxn9@4rbd",
    "paulistacup.png": "https://paulistacup.com.br/campeonatos/6706-paulistinha-cup---sub-09",
    "juventude.png": "https://url-da-liga-juventude.com.br/tabela",
    "apf.png": "https://url-da-apf.com.br/tabela",
    "nike.png": "https://url-da-nike.com.br/eventos",
    "cuebla.png": "https://instituto-esporte-e-cidadania.ritmodoesporte.com.br/futebol-de-campo/campeonato-cuebla/1-edicao-ano-2025/4915/categoria/sub-09-masculino/18228",
}

# --- RÓTULOS CURTOS PARA OS BOTÕES ---
CAMPEONATO_LABELS = {
    "paulista.png": "Federação Paulista",
    "ligapta.png": "Liga Paulista Futsal",
    "gru.png": "Liga Kids Guarulhos",
    "paulistacup.png": "Paulista CUP",
    "juventude.png": "Liga da Juventude",
    "apf.png": "Copa São Paulo",
    "nike.png": "Copa Nike Campo",
    "cuebla.png": "Copa Cuebla",
}


# -------------------------------------------------------------

# ----------------------
OPCOES_QUADRO = ["Principal", "Reserva", "Misto", "Não Aplicável"]
# Removida OPCOES_RESULTADO pois será texto livre (ex: 4x1)
OPCOES_MODALIDADE = ["Futsal", "Campo", "Society", "Areia"] # Nova lista
# ------------------------------------------------------------------


# Garantir pasta Data
DATA_DIR = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)

# ----------------------
# Utilitários de planilha
# ----------------------

def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    return client

def conectar_google_sheets_test():
    try:
        client = conectar_google_sheets()
        # Testa cada aba
        for aba in ["registros", "treino", "sono"]:
            client.open("Registro_Atleta_Bernardo").worksheet(aba)
        st.success("Conexão com Google Sheets OK em todas as abas!")
        return client
    except Exception as e:
        st.error(f"Erro na conexão com Google Sheets: {e}")
        return None

# ----------------------
# Cria o client apenas uma vez
# ----------------------

@st.cache_resource
def get_client():
    return conectar_google_sheets()



# Botão para atualizar dados
# ------------------------------
if st.session_state.get("pagina") != "home":
    if st.button("Atualizar planilha"):
        st.cache_data.clear()
        st.success("Cache limpo! Os dados serão atualizados na próxima leitura.")


def calcular_score_jogo(row):
    # 🔢 Garante valores numéricos seguros
    gols = pd.to_numeric(row.get("Gols Marcados", 0), errors="coerce") or 0
    assistencias = pd.to_numeric(row.get("Assistências", 0), errors="coerce") or 0
    passes_chave = pd.to_numeric(row.get("Passes-chave", 0), errors="coerce") or 0
    desarmes = pd.to_numeric(row.get("Desarmes", 0), errors="coerce") or 0
    faltas = pd.to_numeric(row.get("Faltas Sofridas", 0), errors="coerce") or 0
    participacoes = pd.to_numeric(row.get("Participações Indiretas", 0), errors="coerce") or 0

    chutes = pd.to_numeric(row.get("Chutes", 0), errors="coerce") or 0
    chutes_errados = pd.to_numeric(row.get("Chutes Errados", 0), errors="coerce") or 0
    passes_errados = pd.to_numeric(row.get("Passes Errados", 0), errors="coerce") or 0

    finalizacoes = chutes + chutes_errados
    erros_total = chutes_errados + passes_errados

    # ⭐ SCORE BASE
    score = (
        gols * 2.2 +
        assistencias * 1.8 +
        passes_chave * 0.6 +
        participacoes * 0.4 +
        faltas * 0.3 +
        desarmes * 0.5
    )

    # ⚡ Eficiência
    if finalizacoes > 0:
        score += (gols / finalizacoes) * 1.5

    # ❌ Penalidade
    score -= erros_total * 0.35

    # ⚖️ AJUSTE POR MODALIDADE
    fator = {
        "Futsal": 1.0,
        "Society": 0.9,
        "Campo": 0.8
    }.get(row.get("Condição do Campo"), 1.0)

    score = score / fator

    return max(0, min(10, score))

def parse_duration_to_hours(dur_str):
    """Converte a duração de sono (ex: '7:30', '7:30:00') em horas decimais (ex: 7.5)."""
    try:
        parts = str(dur_str).split(":")
        if len(parts) >= 2:
            hours = float(parts[0])
            minutes = float(parts[1])
            return hours + (minutes / 60)
        return float(dur_str) if pd.notna(dur_str) else 0.0
    except:
        return 0.0
# FIM DA FUNÇÃO QUE PRECISA SER DEFINIDA PRIMEIRO.


@st.cache_data(ttl=300)  # TTL = 300 segundos = 5 minutos
def load_registros():
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("registros")
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    for col in EXPECTED_REGISTROS_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[EXPECTED_REGISTROS_COLUMNS]

def save_registros(df):
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("registros")
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

EXPECTED_TREINOS_COLUMNS = ["Treino", "Date", "Tipo"]

@st.cache_data(ttl=300)
def load_treinos_df():
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("treino")
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    for col in EXPECTED_TREINOS_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[EXPECTED_TREINOS_COLUMNS]

def save_treinos_df(df):
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("treino")
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

# 1. Definição das Constantes de Cochilo
COL_DURACAO_COCHILO = 'Duração do Cochilo'
COL_HOUVE_COCHILO = 'Houve Cochilo'

# 2. Definição da Lista de Todas as Colunas (que usa as constantes)
# ESTA DEVE SER A PRÓXIMA SEÇÃO DE CÓDIGO APÓS AS CONSTANTES
ALL_COLUMNS = [
    "Data",
    "Hora Dormir",
    "Hora Acordar",
    "Duração do Sono (h:min)",
    "Duração do Cochilo",
    "Houve Cochilo"
]

@st.cache_data(ttl=300)
def load_sono_df():
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("sono")
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[ALL_COLUMNS]

def save_sono_df(df):
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("sono")
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

# ----------------------

def safe_extract_date_part(date_val, part='year'):
    """Helper para extrair ano ou mês de datas em formatos variados (dd/mm/YYYY ou datetime)."""
    if pd.isna(date_val) or date_val == "":
        return None
    try:
        # Tenta lidar com o formato que você usa (dd/mm/YYYY)
        if isinstance(date_val, str) and '/' in date_val:
            dt = datetime.strptime(date_val, "%d/%m/%Y")
        else:
            # Tenta conversão automática
            dt = pd.to_datetime(date_val)

        if part == 'year':
            return dt.year
        elif part == 'month':
            return dt.month
    except:
        return None
# Funções de negócio
# ----------------------
def adicionar_jogo(df, novo):
    """novo é dict com campos: Casa, Visitante, Data, Horário, Campeonato, Quadro Jogado,
       Minutos Jogados, Gols Marcados, Assistências, Resultado, Local"""
    # Validação básica
    required = ["Casa","Visitante","Data","Horário","Campeonato","Quadro Jogado","Minutos Jogados","Gols Marcados","Assistências","Resultado","Local"]
    if not all(novo.get(k) not in (None,"") for k in required):
        st.warning("Preencha todos os campos antes de adicionar o registro.")
        return df
    # Evitar duplicata exata Casa+Visitante+Data
    mask = (df["Casa"].astype(str) == str(novo["Casa"])) & (df["Visitante"].astype(str) == str(novo["Visitante"])) & (df["Data"].astype(str) == str(novo["Data"]))
    if mask.any():
        st.warning("Registro já existe com a mesma Casa, Visitante e Data — não foi inserido duplicado.")
        return df
    # Append e salvar
    row = {k:novo.get(k,"") for k in df.columns}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True, sort=False)
    save_registros(df)
    st.success("Registro de jogo adicionado.")
    return df

def adicionar_treino(df, treino, date, tipo):
    if not (treino and date and tipo):
        st.warning("Preencha todos os campos de treino.")
        return df
    # Tenta normalizar a data
    try:
        # permite dd/mm/yyyy ou yyyy-mm-dd
        if isinstance(date, str):
            # se formato dd/mm/YYYY
            if "/" in date:
                d = datetime.strptime(date, "%d/%m/%Y")
                date_str = d.strftime("%d/%m/%Y")
            else:
                # tenta parse automático
                d = pd.to_datetime(date)
                date_str = d.strftime("%d/%m/%Y")
        else:
            date_str = pd.to_datetime(date).strftime("%d/%m/%Y")
    except Exception:
        st.warning("Formato de data inválido. Use dd/mm/YYYY ou selecione usando o seletor.")
        return df
    row = {"Treino": treino, "Date": date_str, "Tipo": tipo}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True, sort=False)
    save_treinos_df(df)
    st.success("Treino adicionado.")
    return df


def to_minutes(dur_str):
    """Converte H:MM para minutos totais, tratando None/NaN/vazio."""
    # (Sua função to_minutes aqui)
    dur_str = str(dur_str).strip().lower()
    if not dur_str or dur_str in ('none', 'nan', 'nat', '0:00'):
        return 0

    try:
        parts = dur_str.split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) >= 2 else 0
        return h * 60 + m
    except:
        return 0

def format_minutes_to_h_mm(total_min):
    """Converte minutos totais de volta para o formato H:MM."""
    horas_totais = int(total_min // 60)
    minutos_restantes = int(total_min % 60)
    return f"{horas_totais}:{minutos_restantes:02d}"

def adicionar_sono(df, data, hora_dormir, hora_acordar):
    if not (data and hora_dormir and hora_acordar):
        st.warning("Preencha todos os campos de sono.")
        return df
    try:
        d = datetime.strptime(data, "%d/%m/%Y") if "/" in data else pd.to_datetime(data)
        data_str = d.strftime("%d/%m/%Y")
        t1 = datetime.strptime(hora_dormir, "%H:%M")
        t2 = datetime.strptime(hora_acordar, "%H:%M")

        if t2 < t1:
            t2 = t2 + timedelta(days=1)

        dur_noite_td = t2 - t1
        dur_min_noite = int(dur_noite_td.total_seconds() / 60)

        # 1. Tenta encontrar o registro
        idx = df[df['Data'] == data_str].index

        if not idx.empty:
            # --- ATUALIZAR: REGISTRO EXISTENTE ENCONTRADO ---
            index_to_update = idx[0]

            # Usa a nova constante
            cochilo_antigo_raw = df.loc[index_to_update, COL_DURACAO_COCHILO]
            cochilo_min = to_minutes(cochilo_antigo_raw)

            total_min_final = dur_min_noite + cochilo_min

            # Atualiza apenas os campos noturnos e a duração total
            df.loc[index_to_update, 'Hora Dormir'] = hora_dormir
            df.loc[index_to_update, 'Hora Acordar'] = hora_acordar
            df.loc[index_to_update, 'Duração do Sono (h:min)'] = format_minutes_to_h_mm(total_min_final)

            st.success(
                f"Registro noturno adicionado e somado ao cochilo ({format_minutes_to_h_mm(cochilo_min)}) de {data_str}!")

        else:
            # --- CRIAR: NENHUM REGISTRO ENCONTRADO ---
            row = {
                "Data": data_str,
                "Hora Dormir": hora_dormir,
                "Hora Acordar": hora_acordar,
                "Duração do Sono (h:min)": format_minutes_to_h_mm(dur_min_noite),
                COL_DURACAO_COCHILO: "0:00", # Usa a nova constante
                COL_HOUVE_COCHILO: "Não"     # Usa a nova constante
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True, sort=False)
            st.success("Sono noturno registrado!")

        save_sono_df(df)
        return df

    except Exception as e:
        st.error(f"Erro ao processar data/hora: {e}")
        return df

def update_sono_cochilo_detalhado(df, date_str, duracao_novo_cochilo_str):
    """
    Atualiza ou CRIA um registro de sono para a data, somando o novo cochilo.
    """
    idx = df[df['Data'] == date_str].index
    minutos_novo_cochilo = to_minutes(duracao_novo_cochilo_str)

    if idx.empty:
        # --- REGISTRO NÃO ENCONTRADO: CRIA UM NOVO (SÓ COCHILO) ---
        new_row = {
            "Data": date_str,
            "Hora Dormir": '', # Usando string vazia em vez de pd.NA
            "Hora Acordar": '', # Usando string vazia em vez de pd.NA
            "Duração do Sono (h:min)": format_minutes_to_h_mm(minutos_novo_cochilo),
            COL_DURACAO_COCHILO: duracao_novo_cochilo_str,
            COL_HOUVE_COCHILO: "Sim"
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True, sort=False)
        save_sono_df(df)
        return df

    # --- REGISTRO ENCONTRADO: PROSSEGUE COM A SOMA ---
    index_to_update = idx[0]

    # Leitura das durações atuais
    # Nota: Colunas que podem ter pd.NA/None devem ser convertidas para str
    duracao_atual_total = str(df.loc[index_to_update, 'Duração do Sono (h:min)'])
    duracao_cochilo_antigo = str(df.loc[index_to_update, COL_DURACAO_COCHILO])

    minutos_sono_total_antigo = to_minutes(duracao_atual_total)
    minutos_cochilo_antigo = to_minutes(duracao_cochilo_antigo)

    # 3. Calcular novos totais
    total_minutos_final = minutos_sono_total_antigo + minutos_novo_cochilo
    total_minutos_cochilo_final = minutos_cochilo_antigo + minutos_novo_cochilo

    # 4. Atualizar o DataFrame
    df.loc[index_to_update, 'Duração do Sono (h:min)'] = format_minutes_to_h_mm(total_minutos_final)
    df.loc[index_to_update, COL_DURACAO_COCHILO] = format_minutes_to_h_mm(total_minutos_cochilo_final)
    df.loc[index_to_update, COL_HOUVE_COCHILO] = 'Sim'

    save_sono_df(df)
    return df


# ----------------------
# Visual / Layout (Streamlit)
# ----------------------

# Sidebar com imagem e informações
with st.sidebar:
    st.title("Bernardo Miranda Conti")
    st.write("✨_Tudo posso naquele que me fortalece._✨")
    if os.path.exists(IMAGE_PATH):
        try:
            img = Image.open(IMAGE_PATH)
            st.image(img, use_container_width=True)
        except Exception:
            st.info("Imagem presente, mas não pode ser exibida.")
    else:
        st.info("Coloque a imagem em 'imagens/bernardo1.jpeg' para ver a foto aqui.")

    st.markdown("---")

    # Título da Seção do Atleta
    st.subheader("👤 Perfil do Atleta")

    # --- LAYOUT EM 3 COLUNAS ---
    col_dados, col_campo, col_futsal = st.columns(3)

    with col_dados:
        st.markdown("##### 🏋️ Dados Físicos")
        # Agrupamos em markdown simples para garantir que caiba no espaço
        st.markdown(f"**Peso:** 33 kg")
        st.markdown(f"**Altura:** 1.32 m")
        st.markdown(f"**Idade:** 9 anos")

    with col_campo:
        st.markdown("##### ⚽ Posições  Campo")
        st.markdown("- M.A")
        st.markdown("- C.A")
        st.markdown("- P.E")

    with col_futsal:
        st.markdown("##### 🥅 Posições  Futsal")
        st.markdown("- Ala")
        st.markdown("- Pivô")


    st.markdown("---")
    st.write("📊 Desenvolvido para fins estatísticos 📊")

# ---------------------------------------------

# --- FUNÇÃO HELPER PARA CRIAR LOGO + LINK DE TEXTO CENTRALIZADO ---
def criar_logo_link_alinhado(col, path, width):
    """Função Helper para exibir a imagem e forçar o texto do link a centralizar."""
    import os
    logo_filename = os.path.basename(path)
    url = CAMPEONATO_URLS.get(logo_filename)
    label = CAMPEONATO_LABELS.get(logo_filename, "Acessar")

    with col:
        # Exibe o logo (Mantido simples, dependendo do CSS global anterior para centralizar o logo)
        if os.path.exists(path):
            st.image(path, width=width)

            # Cria o link de texto usando Markdown/HTML para forçar o alinhamento
            if url:
                # O segredo está aqui: A div tem 100% de largura e o texto é alinhado ao centro.
                link_html = f"""
                <div style='
                    width: 100%;                  /* Ocupa a largura total da coluna */
                    text-align: center !important; /* FORÇA o texto do link a centralizar */
                    font-size: 10px; 
                    margin-top: -10px;            /* Puxa para cima para ficar mais perto do logo */
                '>
                    <a href='{url}' target='_blank'>{label}</a>
                </div>
                """
                st.markdown(link_html, unsafe_allow_html=True)

#----------------------------------------------


#Pagina Home
if st.session_state["pagina"] == "home":
    st.markdown("## 🧠 ScoutMind")
    st.markdown("### Entenda seu jogo. Evolua com inteligência.")
    st.markdown(
        "<p style='color:#9CA3AF; margin-top:-12px; font-size:14px;'>Dados que viram decisões.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # =========================
    # 📌 CARREGAR DADOS
    # =========================
    df_jogos = load_registros()
    df_treinos = load_treinos_df()
    df_sono = load_sono_df()

    # Garantir datas
    if "Data" in df_jogos.columns:
        df_jogos["Data_DT"] = pd.to_datetime(df_jogos["Data"], dayfirst=True, errors="coerce")

    if "Date" in df_treinos.columns:
        df_treinos["Date_DT"] = pd.to_datetime(df_treinos["Date"], dayfirst=True, errors="coerce")

    if "Data" in df_sono.columns:
        df_sono["Data_DT"] = pd.to_datetime(df_sono["Data"], dayfirst=True, errors="coerce")

    hoje = pd.to_datetime("today").date()

    # =========================
    # 🏟️ ÚLTIMO JOGO
    # =========================
    nota_ultimo_jogo = "—"
    if not df_jogos.empty:
        ultimo_jogo = (
            df_jogos.dropna(subset=["Data_DT"])
            .sort_values("Data_DT", ascending=False)
            .iloc[0]
        )
        nota_ultimo_jogo = round(calcular_score_jogo(ultimo_jogo), 1)

    # =========================
    # 😴 SONO DE ONTEM
    # =========================
    sono_ontem_txt = "Sem registro"
    if not df_sono.empty and "Duração do Sono (h:min)" in df_sono.columns:
        df_sono["Data_Date"] = df_sono["Data_DT"].dt.date
        sono_ontem = df_sono[df_sono["Data_Date"] == (hoje - pd.Timedelta(days=1))]
        if not sono_ontem.empty:
            horas = parse_duration_to_hours(sono_ontem.iloc[0]["Duração do Sono (h:min)"])
            h = int(horas)
            m = int((horas - h) * 60)
            sono_ontem_txt = f"{h}h{m:02d}"

    # =========================
    # 💪 TREINOS (7 DIAS)
    # =========================
    treinos_7d = 0
    if not df_treinos.empty:
        df_treinos["Date_Date"] = df_treinos["Date_DT"].dt.date
        treinos_7d = df_treinos[
            df_treinos["Date_Date"] >= (hoje - pd.Timedelta(days=7))
        ].shape[0]

    # =========================
    # 📈 TENDÊNCIA (5 JOGOS)
    # =========================
    tendencia = "Sem dados"
    if len(df_jogos) >= 5:
        df_jogos_ord = df_jogos.sort_values("Data_DT")
        df_jogos_ord["Score"] = df_jogos_ord.apply(calcular_score_jogo, axis=1)
        ultimos = df_jogos_ord.tail(5)["Score"].tolist()

        if ultimos[-1] > ultimos[0]:
            tendencia = "Em evolução 📈"
        elif ultimos[-1] < ultimos[0]:
            tendencia = "Queda 📉"
        else:
            tendencia = "Estável ➖"

    # =========================
    # 🎯 CARDS PRINCIPAIS
    # =========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="card-jogos">
            ⚽ Último jogo
            <p>{nota_ultimo_jogo}</p>
            <label>Nota</label>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card-sono">
            🌙 Sono ontem
            <p>{sono_ontem_txt}</p>
            <label>Duração</label>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="card-treinos">
            💪 Treinos
            <p>{treinos_7d}</p>
            <label>Últimos 7 dias</label>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="card-minutos">
            📈 Tendência
            <p>{tendencia}</p>
            <label>Últimos jogos</label>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # =========================
    # 🚀 AÇÕES RÁPIDAS
    # =========================
    col_a, col_b, col_c, col_d, col_e = st.columns(5)

    with col_a:
        if st.button("⚽ Registrar Jogo", use_container_width=True):
            st.session_state["pagina"] = "jogos"
            st.rerun()

    with col_b:
        if st.button("💪 Registrar Treino", use_container_width=True):
            st.session_state["pagina"] = "treinos"
            st.rerun()

    with col_c:
        if st.button("😴 Registrar Sono", use_container_width=True):
            st.session_state["pagina"] = "sono"
            st.rerun()

    with col_d:
        if st.button("🍎 Registrar Saúde", use_container_width=True):
            st.session_state["pagina"] = "saude"
            st.rerun()

    with col_e:
        if st.button("📊 Ver Análises", use_container_width=True):
            st.session_state["pagina"] = "dashboard"
            st.rerun()

    st.markdown("---")
    st.info("💡 Disciplina hoje vira desempenho amanhã.")


# --------------------------
# Aba Jogos
# --------------------------
if st.session_state["pagina"] == "jogos":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("⚽ Registrar Jogos")
    col1, col2 = st.columns([2, 1])


    # ----------------------------------------------------------------------
    # Pré-carregar opções dinâmicas antes do formulário
    # ----------------------------------------------------------------------
    df_temp = load_registros()

    times_casa = df_temp['Casa'].astype(str).unique()
    times_visitante = df_temp['Visitante'].astype(str).unique()

    opcoes_times = set(
        t.strip() for t in list(times_casa) + list(times_visitante)
        if t and t.strip() != "" and t.lower() != "nan"
    )

    opcoes_times_sorted = sorted(list(opcoes_times))
    opcoes_times_sorted.insert(0, "Selecione ou Crie Novo")

    opcoes_campeonato = sorted(
        [c for c in df_temp['Campeonato'].astype(str).unique()
         if c and c.strip() != "" and c.lower() != "nan"]
    )
    opcoes_campeonato.insert(0, "Selecione ou Crie Novo")

    opcoes_local = sorted(
        [l for l in df_temp['Local'].astype(str).unique()
         if l and l.strip() != "" and l.lower() != "nan"]
    )
    opcoes_local.insert(0, "Selecione ou Crie Novo")

    # ----------------------------------------------------------------------
    with col1:

        st.markdown("##### 🏠 Time Casa")
        novo_casa_input = st.text_input(
            "Criar Novo Time Casa (Deixe vazio para selecionar abaixo)",
            key="novo_casa"
        )
        casa_sel = st.selectbox(
            "Ou Selecione Time Existente:",
            opcoes_times_sorted,
            key="casa_sel"
        )
        st.markdown("---")

        st.markdown("##### ✈️ Time Visitante")
        novo_visitante_input = st.text_input(
            "Criar Novo Time Visitante (Deixe vazio para selecionar abaixo)",
            key="novo_visitante"
        )
        visitante_sel = st.selectbox(
            "Ou Selecione Time Visitante Existente:",
            opcoes_times_sorted,
            key="visitante_sel"
        )
        st.markdown("---")

        st.markdown("##### 🏆 Campeonato")
        novo_campeonato_input = st.text_input(
            "Criar Novo Campeonato (Deixe vazio para selecionar abaixo)",
            key="novo_campeonato"
        )
        campeonato_sel = st.selectbox(
            "Ou Selecione um Campeonato Existente:",
            opcoes_campeonato,
            key="campeonato_sel"
        )
        st.markdown("---")

        st.markdown("##### 🏟️ Local")
        novo_local_input = st.text_input(
            "Criar Novo Local (Deixe vazio para selecionar abaixo)",
            key="novo_local"
        )
        local_sel = st.selectbox(
            "Ou Selecione um Local Existente:",
            opcoes_local,
            key="local_sel"
        )
        st.markdown("---")

        # ------------------------------------------------------------------
        # SCOUT AO VIVO (ADICIONADO – NÃO AFETA O FORMULÁRIO)
        # ------------------------------------------------------------------

        # ===============================
        # 🧠 SCOUT TEMPORÁRIO (ANTI-PERDA)
        # ===============================
        if "scout_temp" not in st.session_state:
            st.session_state["scout_temp"] = {
                "Chutes": 0,
                "Chutes Errados": 0,
                "Desarmes": 0,
                "Passes-chave": 0,
                "Passes Errados": 0,
                "Faltas Sofridas": 0,
                "Participações Indiretas": 0
            }

        # ------------------ FORMULÁRIO ------------------

        st.markdown("### 📊 Scout Ao Vivo")

        st.number_input("🥅 Chutes", min_value=0, key="Chutes")
        st.number_input("❌ Chutes Errados", min_value=0, key="Chutes Errados")
        st.number_input("🛡️ Desarmes", min_value=0, key="Desarmes")
        st.number_input("🎯 Passes-chave", min_value=0, key="Passes-chave")
        st.number_input("❌ Passes Errados", min_value=0, key="Passes Errados")
        st.number_input("⚡ Faltas Sofridas", min_value=0, key="Faltas Sofridas")
        st.number_input("🔁 Participações Indiretas", min_value=0, key="Participações Indiretas")

        st.markdown("---")
        st.markdown("### 💾 Encerrar Partida")

        with st.form("form_salvar_jogo"):

            data = st.date_input("Data do Jogo", format="DD/MM/YYYY")
            horario = st.time_input("Horário", value=time(20, 0))
            quadro = st.selectbox("Quadro Jogado", OPCOES_QUADRO)
            minutos = st.number_input("Minutos Jogados", min_value=0, max_value=120)
            gols = st.number_input("Gols Marcados", min_value=0)
            assistencias = st.number_input("Assistências", min_value=0)

            c1, c2 = st.columns(2)
            with c1:
                gols_atleta = st.number_input("Gols Time do Atleta", min_value=0)
            with c2:
                gols_adversario = st.number_input("Gols do Adversário", min_value=0)

            modalidade = st.selectbox("Modalidade", OPCOES_MODALIDADE)

            salvar = st.form_submit_button("💾 Salvar Jogo")

            if salvar:

                novo = {
                    "Casa": novo_casa_input.strip() if novo_casa_input.strip() else casa_sel,
                    "Visitante": novo_visitante_input.strip() if novo_visitante_input.strip() else visitante_sel,
                    "Campeonato": novo_campeonato_input.strip() if novo_campeonato_input.strip() else campeonato_sel,
                    "Local": novo_local_input.strip() if novo_local_input.strip() else local_sel,
                    "Data": data.strftime("%d/%m/%Y"),
                    "Horário": horario.strftime("%H:%M"),
                    "Quadro Jogado": quadro,
                    "Minutos Jogados": minutos,
                    "Gols Marcados": gols,
                    "Assistências": assistencias,
                    "Resultado": f"{gols_atleta}x{gols_adversario}",
                    "Condição do Campo": modalidade,
                    "Chutes": st.session_state["Chutes"],
                    "Chutes Errados": st.session_state["Chutes Errados"],
                    "Desarmes": st.session_state["Desarmes"],
                    "Passes-chave": st.session_state["Passes-chave"],
                    "Passes Errados": st.session_state["Passes Errados"],
                    "Faltas Sofridas": st.session_state["Faltas Sofridas"],
                    "Participações Indiretas": st.session_state["Participações Indiretas"],

                }


                with st.spinner("💾 Salvando jogo..."):
                    df_reg = load_registros()
                    adicionar_jogo(df_reg, novo)

                    st.toast("⚽ Jogo registrado com sucesso!", icon="✅")

                # 🔥 LIMPA O SCOUT SÓ AGORA
                for k in [
                    "Chutes", "Chutes Errados", "Desarmes",
                    "Passes-chave", "Passes Errados",
                    "Faltas Sofridas", "Participações Indiretas"
                ]:
                    if k in st.session_state:
                        del st.session_state[k]

                st.rerun()

    # ----------------------------------------------------------------------
    # COLUNA 2 - TABELA
    # ----------------------------------------------------------------------
    with col2:
        st.markdown("### 📋 Tabela dos Jogos")
        df = load_registros()

        df_exibicao = df.iloc[::-1].copy()
        df_exibicao.index += 1
        df_exibicao.insert(0, 'Nº', df_exibicao.index)
        df_exibicao.index.name = None

        st.dataframe(df_exibicao, use_container_width=True)

        if st.button("Exportar CSV (últimos 200)"):
            tmp = df.tail(200).copy()
            tmp.reset_index(drop=True, inplace=True)
            tmp.index += 1
            tmp.insert(0, 'Nº', tmp.index)
            tmp.index.name = None

            towrite = io.BytesIO()
            tmp.to_csv(towrite, index=False, sep=';', encoding='utf-8')
            towrite.seek(0)

            st.download_button(
                "Download CSV",
                towrite,
                file_name="registros_export.csv",
                mime="text/csv"
            )

# Aba Treinos
# --------------------------
if st.session_state["pagina"] == "treinos":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("🎯Treinos")
    df_treinos = load_treinos_df()

    # --- NOVO BLOCO DE NORMALIZAÇÃO DE DADOS (CRUCIAL PARA UNIFICAR NOMES) ---
    NOME_COLUNA_TREINO = 'Treino'
    NOME_COLUNA_TIPO = 'Tipo'

    if NOME_COLUNA_TREINO in df_treinos.columns:
        # APLICA NORMALIZAÇÃO: Remove espaços (strip), padroniza a capitalização (title)
        df_treinos[NOME_COLUNA_TREINO] = df_treinos[NOME_COLUNA_TREINO].astype(str).str.strip().str.title()

    if NOME_COLUNA_TIPO in df_treinos.columns:
        # APLICA NORMALIZAÇÃO: Remove espaços (strip), padroniza a capitalização (title)
        df_treinos[NOME_COLUNA_TIPO] = df_treinos[NOME_COLUNA_TIPO].astype(str).str.strip().str.title()
    # -------------------------------------------------------------------------

    # ----------------------------------------------------
    # Pré-carregar opções dinâmicas para Treino e Tipo (AGORA USANDO DADOS NORMALIZADOS)
    # ----------------------------------------------------
    # Opções para Nome/Descrição do Treino
    opcoes_treino = sorted(
        [t for t in df_treinos[NOME_COLUNA_TREINO].astype(str).unique() if
         t and t.strip() != "" and t.lower() != "nan"])
    opcoes_treino.insert(0, "Selecione ou Crie Novo")

    # Opções para o Tipo do Treino (Futsal, Campo, etc.)
    opcoes_tipo = sorted(
        [t for t in df_treinos[NOME_COLUNA_TIPO].astype(str).unique() if t and t.strip() != "" and t.lower() != "nan"])
    opcoes_tipo.insert(0, "Selecione ou Crie Novo")

    # ----------------------------------------------------
    # BLOCO 1: REGISTRO DE NOVO TREINO E VISUALIZAÇÃO RÁPIDA
    # ----------------------------------------------------
    col1, col2 = st.columns([2, 1])
    with col1:

        # --------------------------------------------------------------------------
        # 1. PADRONIZAÇÃO DO CAMPO TREINO (NOME/DESCRIÇÃO)
        # --------------------------------------------------------------------------
        st.markdown("##### 📝 Nome/Descrição do Treino")
        novo_treino_input = st.text_input("Criar Novo Treino (Deixe vazio para selecionar abaixo)",
                                          key="novo_treino_input")
        treino_sel = st.selectbox("Ou Selecione Treino Existente:", opcoes_treino, key="treino_sel")
        st.markdown("---")

        # --------------------------------------------------------------------------
        # 2. PADRONIZAÇÃO DO CAMPO TIPO (FUTSAL, CAMPO, ETC)
        # --------------------------------------------------------------------------
        st.markdown("##### ⚙️ Tipo do Treino")
        novo_tipo_input = st.text_input("Criar Novo Tipo (Deixe vazio para selecionar abaixo)", key="novo_tipo_input")
        tipo_sel = st.selectbox("Ou Selecione Tipo Existente:", opcoes_tipo, key="tipo_sel")
        st.markdown("---")

        # --------------------------------------------------------------------------
        # 3. FORMULÁRIO DE SUBMISSÃO
        # --------------------------------------------------------------------------
        with st.form("form_treino", clear_on_submit=True):

            # CAMPOS FIXOS
            date_t = st.date_input("Data do Treino")

            submit_t = st.form_submit_button("Adicionar Treino")

            if submit_t:
                # --------------------------------------------------------------------------
                # LÓGICA DE DECISÃO (QUAL CAMPO USAR?)
                # --------------------------------------------------------------------------

                # 1. Definir o Nome/Descrição do Treino
                if novo_treino_input.strip() != "":
                    # ATENÇÃO: Normaliza o novo input antes de salvar
                    treino_final = novo_treino_input.strip().title()
                elif treino_sel != "Selecione ou Crie Novo":
                    treino_final = treino_sel
                else:
                    st.error("Por favor, preencha o Novo Treino OU selecione um existente.")
                    st.stop()

                # 2. Definir o Tipo do Treino
                if novo_tipo_input.strip() != "":
                    # ATENÇÃO: Normaliza o novo input antes de salvar
                    tipo_final = novo_tipo_input.strip().title()
                elif tipo_sel != "Selecione ou Crie Novo":
                    tipo_final = tipo_sel
                else:
                    st.error("Por favor, preencha o Novo Tipo de Treino OU selecione um existente.")
                    st.stop()

                # --------------------------------------------------------------------------

                # 3. Prossegue com o salvamento
                # converter date para formato dd/mm/YYYY
                date_str = date_t.strftime("%d/%m/%Y")

                # ADICIONAR TREINO COM OS VALORES PADRONIZADOS
                df_treinos = adicionar_treino(df_treinos, treino_final, date_str, tipo_final)

                st.success("Registro de Treino adicionado! Recarregando lista...")
                # FORÇA O RECARREGAMENTO DO SCRIPT PARA INCLUIR OS NOVOS TREINOS/TIPOS NA LISTA!
                st.rerun()

    # Criar coluna de data para ordenação (se ainda não existir)
    if "date_obj" not in df_treinos.columns:
        df_treinos["date_obj"] = pd.to_datetime(
            df_treinos["Date"], dayfirst=True, errors="coerce"
        )

    with col2:
        st.markdown("### 🏃Treinos Realizados")
        # EXIBE O DATAFRAME JÁ NORMALIZADO
        df_treinos_view = (
            df_treinos
            .sort_values("date_obj", ascending=False)
            .drop(columns=["date_obj"], errors="ignore")
        )

        st.dataframe(df_treinos_view.head(200), width="stretch")

        if st.button("Exportar Treinos CSV"):
            towrite = io.BytesIO()
            df_treinos.to_csv(towrite, index=False, sep=';')
            towrite.seek(0)
            st.download_button("Download CSV Treinos", towrite, file_name="treinos_export.csv", mime="text/csv")

    st.markdown("---")

    # ----------------------------------------------------
    # BLOCO 2: GERAÇÃO DE GRÁFICOS E RESUMO ESCRITO
    # ----------------------------------------------------
    st.markdown("### Gerar Gráfico de Tipos de Treino")

    # Filtro por Nome do Treino (USA DADOS NORMALIZADOS)
    nomes_treinos = ["Todos"] + sorted(df_treinos[NOME_COLUNA_TREINO].dropna().unique().tolist())
    treino_selecionado = st.selectbox("Filtrar por Nome do Treino:", nomes_treinos)

    # Filtro de Mês (Mantido o filtro antigo para compatibilidade)
    mes_filter = st.selectbox("Filtrar por mês (mm) — deixe em branco para todos:",
                              [""] + [f"{i:02d}" for i in range(1, 13)])

    if st.button("Gerar Gráfico (Treinos)"):
        # ATENÇÃO: Se load_treinos_df() está cacheado, ele retornará o cache.
        # É mais seguro usar a variável df_treinos do escopo superior que já foi normalizada.

        # O BLOCO ABAIXO REFAZ A NORMALIZAÇÃO APENAS POR SEGURANÇA MÁXIMA, CASO load_treinos_df() ESTEJA SENDO RE-CHAMADO
        # df_treinos_grafico = load_treinos_df()
        # if NOME_COLUNA_TREINO in df_treinos_grafico.columns:
        #     df_treinos_grafico[NOME_COLUNA_TREINO] = df_treinos_grafico[NOME_COLUNA_TREINO].astype(str).str.strip().str.title()
        # if NOME_COLUNA_TIPO in df_treinos_grafico.columns:
        #     df_treinos_grafico[NOME_COLUNA_TIPO] = df_treinos_grafico[NOME_COLUNA_TIPO].astype(str).str.strip().str.title()
        # df_treinos = df_treinos_grafico # Usa o df normalizado para o gráfico

        if df_treinos.empty:
            st.info("Nenhum treino cadastrado.")
        else:
            df_treinos = df_treinos.fillna("")


            # --- FUNÇÕES AUXILIARES DE DATA (Assegura que a data está correta) ---
            def parse_date_str(s):
                try:
                    return datetime.strptime(s, "%d/%m/%Y")
                except:
                    try:
                        return pd.to_datetime(s)
                    except:
                        return None


            df_treinos["date_obj"] = df_treinos["Date"].apply(parse_date_str)

            df_treinos["date_obj"] = pd.to_datetime(df_treinos["date_obj"], errors="coerce")
            df_treinos = df_treinos.dropna(subset=["date_obj"])

            # --- APLICAÇÃO DOS FILTROS ---

            df_filtrado = df_treinos.copy()

            if treino_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado[NOME_COLUNA_TREINO] == treino_selecionado]

            if mes_filter:
                df_filtrado = df_filtrado[df_filtrado["date_obj"].dt.month == int(mes_filter)]

            # Se não houver treinos, apenas avisa (não trava o app)
            if df_filtrado.empty:
                st.info("Nenhum treino no período selecionado.")
            else:

                # ----------------------------------------------------
                # NOVO: PROCESSAMENTO PARA GRÁFICO E RESUMO DETALHADO
                # ----------------------------------------------------

                # 1. Agrupamento Total por TIPO (Futsal, Campo, etc.)
                # Usa a coluna NOME_COLUNA_TIPO (Tipo) que já está normalizada
                df_contagem_tipo = df_filtrado[NOME_COLUNA_TIPO].value_counts().reset_index()
                df_contagem_tipo.columns = [NOME_COLUNA_TIPO, "Contagem_Tipo"]

                # 2. Agrupamento Detalhado por TIPO e NOME (Futsal - Ypiranga)
                # Usa as colunas já normalizadas
                df_contagem_detalhe = df_filtrado.groupby([NOME_COLUNA_TIPO, NOME_COLUNA_TREINO]).size().reset_index(
                    name='Contagem_Detalhe')

                total_treinos = df_filtrado.shape[0]

                # --- GRÁFICO MODERNO: LINHA DO TEMPO POR TIPO DE TREINO ---

                st.markdown("### 📈 Evolução dos Treinos por Tipo")

                df_plot = df_filtrado.copy()
                df_plot["date_obj"] = pd.to_datetime(df_plot["date_obj"], errors="coerce")
                df_plot = df_plot.dropna(subset=["date_obj"])

                # 1️⃣ DATA REAL DA SEMANA (datetime)
                df_plot["Semana_DT"] = (
                    df_plot["date_obj"]
                    .dt.to_period("W")
                    .apply(lambda x: x.start_time)
                )

                # ===============================
                # 🚨 ALERTA DE REGULARIDADE (LÓGICA CORRETA)
                # ===============================

                # Semanas que tiveram ao menos 1 treino
                semanas_com_treino = (
                    df_filtrado["date_obj"]
                    .dt.to_period("W")
                    .nunique()
                )

                # TOTAL DE SEMANAS DO MÊS SELECIONADO
                if mes_filter:
                    ano_ref = df_filtrado["date_obj"].dt.year.mode()[0]
                    mes_ref = int(mes_filter)

                    semanas_do_mes = (
                        pd.date_range(
                            start=f"{ano_ref}-{mes_ref:02d}-01",
                            end=pd.Timestamp(f"{ano_ref}-{mes_ref:02d}-01") + pd.offsets.MonthEnd(1),
                            freq="W-MON"
                        )
                        .to_period("W")
                        .nunique()
                    )
                else:
                    # fallback seguro (sem filtro)
                    semanas_do_mes = semanas_com_treino

                semanas_sem_treino = max(0, semanas_do_mes - semanas_com_treino)

                # Feedback claro e confiável
                if semanas_sem_treino == 0:
                    st.success("✅ Excelente consistência: treinou em todas as semanas do mês.")
                elif semanas_sem_treino == 1:
                    st.warning("⚠️ Atenção: 1 semana sem treino no mês.")
                else:
                    st.error(f"🚨 Alerta: {semanas_sem_treino} semanas sem treino no mês.")

                # 2️⃣ AGRUPAMENTO USANDO DATETIME (CORRETO)
                df_linha = (
                    df_plot
                    .groupby(["Semana_DT", NOME_COLUNA_TIPO])
                    .size()
                    .reset_index(name="Quantidade")
                )

                # 3️⃣ ORDENAÇÃO CRONOLÓGICA (ESSENCIAL)
                df_linha = df_linha.sort_values("Semana_DT")

                # 4️⃣ DATA BR SÓ PARA EXIBIÇÃO
                df_linha["Semana"] = df_linha["Semana_DT"].dt.strftime("%d/%m/%Y")

                if df_linha.empty:
                    st.info("Sem dados suficientes para gerar o gráfico.")
                else:
                    fig = px.line(
                        df_linha,
                        x="Semana",
                        y="Quantidade",
                        color=NOME_COLUNA_TIPO,
                        markers=True,
                        title="Semanas com Treino por Tipo (não representa o total de sessões)"
                    )

                    fig.update_traces(
                        line=dict(width=3),
                        marker=dict(size=8)
                    )

                    fig.update_layout(
                        plot_bgcolor="#0E1117",
                        paper_bgcolor="#0E1117",
                        font=dict(color="white"),
                        hovermode="x unified",
                        legend_title_text="Tipo de Treino"
                    )

                    st.plotly_chart(fig, use_container_width=True)

                st.caption(
                    "📌 Cada ponto representa uma semana com ao menos um treino. "
                    "O total de treinos está no resumo abaixo."
                )

                # --- RESUMO ESCRITO DETALHADO ---
                st.markdown("### 📋 Detalhamento da Frequência")

                resumo_texto = []

                # Itera sobre o agrupamento por TIPO (Futsal, Campo)
                for index_tipo, row_tipo in df_contagem_tipo.iterrows():

                    tipo_original = row_tipo[NOME_COLUNA_TIPO]
                    total_tipo = row_tipo['Contagem_Tipo']

                    resumo_texto.append(f"**{tipo_original}: {total_tipo} treinos**")

                    # Filtra os detalhes (Ypiranga, Flamengo) para este TIPO
                    detalhes = df_contagem_detalhe[df_contagem_detalhe[NOME_COLUNA_TIPO] == tipo_original]

                    # Itera sobre os detalhes do TIPO
                    for index_det, row_det in detalhes.iterrows():
                        resumo_texto.append(f"• {row_det[NOME_COLUNA_TREINO]}: {row_det['Contagem_Detalhe']}x")

                    resumo_texto.append(" ")  # Linha em branco para separação

                st.markdown("\n".join(resumo_texto))
                st.markdown("---")

# Aba Sono
# --------------------------
def safe_parse_hour(hora_str):
    """
    Converte 'HH:MM' em hora decimal.
    Retorna None se inválido.
    """
    try:
        if not hora_str or ":" not in str(hora_str):
            return None
        h, m = str(hora_str).split(":")
        return int(h) + int(m) / 60
    except:
        return None


if st.session_state["pagina"] == "sono":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("💤Controle de Sono")

    # AS CONSTANTES JÁ FORAM DEFINIDAS NO TOPO. USAMOS ELAS AQUI.
    COLUNAS_COCHILO_NAMES = [COL_DURACAO_COCHILO, COL_HOUVE_COCHILO]

    # Garante que a função load_sono_df() está carregando o DF aqui
    df_sono = load_sono_df()



    # --- GARANTE AS COLUNAS NO DF PRINCIPAL USANDO VALORES STRING ---
    for col in COLUNAS_COCHILO_NAMES:
        if col not in df_sono.columns:
            if col == COL_DURACAO_COCHILO:
                df_sono[col] = '0:00'
            elif col == COL_HOUVE_COCHILO:
                df_sono[col] = 'Não'

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 😴 Registro de Sono Noturno")
        with st.form("form_sono", clear_on_submit=True):
            data_s = st.date_input("Data do Sono", key="data_sono_noite")
            hora_d = st.time_input("Hora Dormir", key="hora_dormir")
            hora_a = st.time_input("Hora Acordar", key="hora_acordar")

            ssub = st.form_submit_button("Salvar Registro de Sono da Noite")

            if ssub:
                data_str = data_s.strftime("%d/%m/%Y")
                hora_d_str = hora_d.strftime("%H:%M")
                hora_a_str = hora_a.strftime("%H:%M")

                df_sono = adicionar_sono(df_sono, data_str, hora_d_str, hora_a_str)
                st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Adicionar Cochilo/Soneca (Atualizar o total do dia)")

        with st.form("form_cochilo", clear_on_submit=True):
            date_c = st.date_input("Data do Cochilo", key="data_cochilo")

            duracao_cochilo = st.text_input("Duração do Cochilo (Ex: 1:30 para 1h e 30 min)",
                                            value="0:00",
                                            key="duracao_cochilo")

            submit_c = st.form_submit_button("Adicionar Cochilo")

            if submit_c:
                data_str = date_c.strftime("%d/%m/%Y")

                if 'update_sono_cochilo_detalhado' in globals():
                    df_sono = update_sono_cochilo_detalhado(df_sono, data_str, duracao_cochilo)
                    st.success(f"Cochilo de {duracao_cochilo} adicionado e somado ao total de sono de {data_str}!")
                    st.rerun()
                else:
                    st.error(
                        "Erro: Função 'update_sono_cochilo_detalhado' não encontrada. Verifique o topo do seu script.")

    with col2:
        st.markdown("### 🌙️ Registros de Sono")

        # RECARREGA O DATAFRAME SALVO
        df_sono_atualizado = load_sono_df()

        # GARANTE AS COLUNAS NO DF CARREGADO PARA EXIBIÇÃO
        for col in COLUNAS_COCHILO_NAMES:
            if col not in df_sono_atualizado.columns:
                df_sono_atualizado[col] = '0:00' if col == COL_DURACAO_COCHILO else 'Não'

        # EXIBIÇÃO: A tabela AGORA DEVE refletir as mudanças do arquivo salvo.
        st.dataframe(df_sono_atualizado.tail(200), use_container_width=True)

        if st.button("Exportar Sono CSV"):
            towrite = io.BytesIO()
            df_sono_atualizado.to_csv(towrite, index=False, sep=';')
            towrite.seek(0)
            st.download_button("Download CSV Sono", towrite, file_name="sono_export.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("### Gerar Gráfico do Sono")
    mes_filter_s = st.selectbox("Filtrar por mês (mm) — deixe em branco para todos:",
                                [""] + [f"{i:02d}" for i in range(1, 13)], key="mes_sono")

    anos_disponiveis = sorted(
        list(
            set(
                pd.to_datetime(df_sono["Data"], dayfirst=True, errors="coerce")
                .dt.year
                .dropna()
                .astype(int)
            )
        ),
        reverse=True
    )

    ano_filter = st.selectbox("Filtrar por ano", anos_disponiveis)



    if st.button("Gerar Gráfico (Sono)"):
        df_sono = load_sono_df()

        # ===============================
        # 🧠 CARD – QUALIDADE DO SONO (ÚLTIMO REGISTRO)
        # ===============================

        df_sono_card = df_sono.copy()

        # Garante datas válidas
        df_sono_card["date_obj"] = pd.to_datetime(
            df_sono_card["Data"], dayfirst=True, errors="coerce"
        )

        df_sono_card = df_sono_card.dropna(subset=["date_obj"])

        # APLICA OS MESMOS FILTROS DO GRÁFICO AO CARD
        if mes_filter_s:
            df_sono_card = df_sono_card[
                df_sono_card["date_obj"].dt.month == int(mes_filter_s)
                ]

        if ano_filter:
            df_sono_card = df_sono_card[
                df_sono_card["date_obj"].dt.year == int(ano_filter)
                ]



        if not df_sono_card.empty:
            # Ordena do mais recente para o mais antigo
            df_sono_card = df_sono_card.sort_values("date_obj", ascending=False)

            ultimo = df_sono_card.iloc[0]

            # Duração do sono
            dur_str = str(ultimo.get("Duração do Sono (h:min)", "0:00"))
            partes = dur_str.split(":")
            horas = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
            dur_h = horas + minutos / 60

            # Horário que dormiu
            hora_d_str = str(ultimo.get("Hora Dormir", "00:00"))
            hora_dormiu = safe_parse_hour(ultimo.get("Hora Dormir"))


            # 👉 AVALIAÇÃO
            # 👉 AVALIAÇÃO DO HORÁRIO (CORRETA E LEGÍVEL)
            # 👉 AVALIAÇÃO DO SONO (ORDEM CORRETA)
            # 👉 AVALIAÇÃO DO SONO (ORDEM DEFINITIVA)
            # 👉 AVALIAÇÃO DO SONO (LÓGICA CORRETA)
            status = "✅ Sono Ideal"
            cor = "green"
            mensagem = "Horário e duração adequados."

            # Prioridade 1: quantidade
            if dur_h < 6:
                status = "🚨 Sono Insuficiente"
                cor = "red"
                mensagem = "Quantidade de sono abaixo do ideal."

            # Prioridade 2: horário (somente se existir)
            elif hora_dormiu is not None:

                # Dormiu depois da meia-noite
                if 0 <= hora_dormiu < 2:
                    status = "⚠️ Sono Tardio"
                    cor = "orange"
                    mensagem = "Dormiu após 00:00. Atenção ao ritmo biológico."

                # Dormiu muito tarde (madrugada pesada)
                elif 2 <= hora_dormiu < 6:
                    status = "🚨 Sono Muito Tardio"
                    cor = "red"
                    mensagem = "Dormiu após 02:00. Alto impacto negativo na recuperação."

                # Dormiu no limite
                elif 23 <= hora_dormiu < 24:
                    status = "⚠️ Dormiu no Limite"
                    cor = "orange"
                    mensagem = "Dormiu próximo do limite ideal (23:00)."

                # Antes de 23h → ideal
                else:
                    status = "✅ Sono Ideal"
                    cor = "green"
                    mensagem = "Dormiu em horário adequado para boa recuperação."

            # 👉 CARD VISUAL
            st.markdown("### 🧠 Análise do Último Sono (dentro do periodo selecionado)")

            st.markdown(
                f"""
                    <div style="
                        padding:18px;
                        border-radius:12px;
                        background-color:#1F2430;
                        border-left:6px solid {cor};
                    ">
                        <h4>{status}</h4>
                        <p><b>Duração:</b> {horas}h {minutos:02d}min</p>
                        <p><b>Hora de dormir:</b> {hora_d_str}</p>
                        <p style="opacity:0.8;">{mensagem}</p>
                    </div>
                    """,
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Garante que as novas colunas existem
        for col in COLUNAS_COCHILO_NAMES:
            if col not in df_sono.columns:
                df_sono[col] = '0:00' if col == COL_DURACAO_COCHILO else 'Não'

        if df_sono.empty:
            st.info("Nenhum registro de sono.")
        else:
            datas = []
            duracoes = []
            indicador_cochilo = []
            horarios_dormir = []

            for _, row in df_sono.iterrows():



                d = row.get("Data", "")
                dur_str = str(row.get("Duração do Sono (h:min)", ""))

                # LÊ USANDO A CONSTANTE (CORREÇÃO DE GRÁFICO)
                cochilo_str = str(row.get(COL_HOUVE_COCHILO, "Não")).strip().title()

                try:
                    if d:
                        data_obj = datetime.strptime(d, "%d/%m/%Y")

                        if mes_filter_s and data_obj.month != int(mes_filter_s):
                            continue

                        if ano_filter and data_obj.year != int(ano_filter):
                            continue

                        parts = dur_str.split(":")
                        if len(parts) >= 2:
                            horas = int(parts[0])
                            minutos = int(parts[1])
                            dur_h = horas + minutos / 60

                            datas.append(data_obj.strftime("%d/%m/%Y"))
                            duracoes.append(dur_h)
                            indicador_cochilo.append(cochilo_str == 'Sim')

                            hora_dormir_str = str(row.get("Hora Dormir", "00:00"))
                            horarios_dormir.append(hora_dormir_str)


                except Exception:
                    continue

            if not datas:
                st.info("Nenhum dado válido para gerar gráfico.")
            else:
                media = sum(duracoes) / len(duracoes)
                horas_med = int(media)
                minutos_med = int((media - horas_med) * 60)
                fig, ax = plt.subplots(figsize=(12, 6))

                # Plot da linha
                ax.plot(range(len(datas)), duracoes, linestyle='--', linewidth=2, color='#2196F3', zorder=1)

                # Loop de Plotagem dos Pontos (Asterisco/Cochilo)
                for i, val in enumerate(duracoes):
                    houve_cochilo = indicador_cochilo[i]

                    # Estilos dos Pontos
                    color = "red" if val < 6 else ("green" if val > 8 else "orange")
                    marcador = 'D' if houve_cochilo else 'o'  # Diamante para Cochilo
                    tamanho = 100 if houve_cochilo else 60

                    # Plota o Ponto
                    ax.scatter(i, val, color=color, s=tamanho, marker=marcador, zorder=2)

                    # Rótulo de texto com o Asterisco
                    horas_l = int(val)
                    minutos_l = int((val - horas_l) * 60)
                    texto_extra = " *" if houve_cochilo else ""

                    ax.text(i, val + 0.15, f"{horas_l}h{minutos_l:02d}{texto_extra}", ha='center', color='white',
                            fontsize=9)

                    # Indicador de horário tardio
                    hora_dormir_str = horarios_dormir[i]

                    hora_dormiu = safe_parse_hour(horarios_dormir[i])

                    if hora_dormiu is not None:

                        # 🔴 Madrugada (00:00 até 05:59)
                        if hora_dormiu < 6.0:
                            ax.scatter(
                                i, val,
                                s=200,
                                facecolors='none',
                                edgecolors='red',
                                linewidths=2
                            )

                        # 🟢 Dormiu cedo (06:00 até 22:45)
                        elif 6.0 <= hora_dormiu <= 22.75:
                            ax.scatter(
                                i, val,
                                s=140,
                                facecolors='none',
                                edgecolors='green',
                                linewidths=2
                            )

                        # 🟠 Limite aceitável (23:00 até 23:45)
                        elif 23.0 <= hora_dormiu <= 23.75:
                            ax.scatter(
                                i, val,
                                s=160,
                                facecolors='none',
                                edgecolors='orange',
                                linewidths=2
                            )

                # Linhas de referência (Média, Alerta)
                ax.axhline(media, color='#009688', linestyle='-', linewidth=1,
                           label=f'Média ({horas_med}h{minutos_med:02d})')
                ax.axhline(6, color='red', linestyle=':', linewidth=1, label='Alerta (6h)')
                ax.axhline(8, color='lightgreen', linestyle=':', linewidth=1, label='Meta (8h)')

                ax.set_title("Controle de Sono", color='white')
                ax.set_xticks(range(len(datas)))
                ax.set_xticklabels(datas, rotation=45, ha='right', color='white')
                ax.set_ylabel("Duração (horas)", color='white')
                ax.grid(True, linestyle=':', alpha=0.3)
                # Configurações Dark Mode (se você estiver usando)
                fig.patch.set_facecolor('#0E1117')
                ax.set_facecolor('#0E1117')
                ax.tick_params(axis='x', colors='white')
                ax.tick_params(axis='y', colors='white')
                ax.spines['bottom'].set_color('white')
                ax.spines['left'].set_color('white')

                # Removido o ax.text de média pois a linha ax.axhline já é mais clara
                ax.legend(facecolor='#1F2430', edgecolor='white', labelcolor='white')

                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)


# --------------------------
# Aba Análises (resumo / gráficos rápidos)
# --------------------------

@st.cache_data(ttl=300)
def load_saude_df():
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("saude")
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    for col in EXPECTED_SAUDE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[EXPECTED_SAUDE_COLUMNS]

def save_saude_df(df):
    client = get_client()
    sheet = client.open("Registro_Atleta_Bernardo").worksheet("saude")
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

if st.session_state["pagina"] == "saude":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("🩺 Saúde & Preparação do Atleta")
    st.caption(
        "Registro diário de sono, alimentação e acompanhamento físico. "
        "Esses dados ajudam a entender o impacto da preparação no desempenho."
    )

    st.markdown("---")

    st.subheader("📝 Registro Diário de Saúde")

    col1, col2 = st.columns(2)

    with col1:
        data_saude = st.date_input("📅 Data", datetime.now().date())
        alimentacao = st.selectbox(
            "🍽️ Alimentação do dia",
            ["Boa", "Regular", "Ruim"]
        )
        hidratacao = st.selectbox(
            "💧 Hidratação",
            ["Boa", "Regular", "Ruim"]
        )

    with col2:
        cansaco = st.selectbox(
            "🥵 Cansaço físico",
            ["Baixo", "Moderado", "Alto"]
        )
        observacao = st.text_area(
            "🗒️ Observações (opcional)",
            placeholder="Ex: pouco apetite, jogo intenso, dor muscular..."
        )

    salvar_saude = st.button("💾 Salvar Registro de Saúde")

    if salvar_saude:
        df_saude = load_saude_df()
        data_str = data_saude.strftime("%d/%m/%Y")

        # Remove registro antigo do mesmo dia (se existir)
        df_saude = df_saude[df_saude["Data"] != data_str]

        novo = {
            "Data": data_str,
            "Alimentação": alimentacao,
            "Hidratação": hidratacao,
            "Cansaço": cansaco,
            "Observação": observacao
        }

        df_saude = pd.concat([df_saude, pd.DataFrame([novo])], ignore_index=True)
        save_saude_df(df_saude)

        st.success("Registro de saúde salvo com sucesso ✅")

    st.markdown(
        """
        <div style="
            margin-top:20px;
            padding:16px;
            border-radius:14px;
            background:#0B1220;
            border-left:6px solid #03A9F4;
        ">
            <strong>💡 Dica:</strong><br>
            Registrar sua saúde ajuda a entender <b>por que você foi bem ou mal</b> em campo.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.subheader("📊 Registros Recentes de Saúde")

    df_saude = load_saude_df()

    if df_saude.empty:
        st.info("Nenhum registro de saúde cadastrado ainda.")
    else:
        # Converte data para datetime
        df_saude["Data_dt"] = pd.to_datetime(
            df_saude["Data"], dayfirst=True, errors="coerce"
        )

        # Ordena do mais recente para o mais antigo
        df_saude = df_saude.sort_values("Data_dt", ascending=False)

        # Mantém apenas colunas relevantes
        df_exibicao = df_saude[
            ["Data", "Alimentação", "Hidratação", "Cansaço", "Observação"]
        ].copy()

        st.dataframe(
            df_exibicao,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.subheader("📄 Documentos de Saúde")
    st.markdown(
        "Aqui você pode anexar relatórios da nutricionista, exames ou avaliações físicas."
    )

    descricao_pdf = st.text_input(
        "📝 Descrição do documento",
        placeholder="Ex: Avaliação nutricional - Janeiro 2025"
    )

    link_documento = st.text_input(
        "🔗 Link do documento (Google Drive)",
        placeholder="Cole aqui o link do PDF no Drive"
    )

    salvar_pdf = st.button("💾 Salvar Documento")

    if salvar_pdf:
        if descricao_pdf.strip() == "" or link_documento.strip() == "":
            st.warning("Informe a descrição e o link do documento.")
        else:
            client = get_client()
            sheet = client.open("Registro_Atleta_Bernardo").worksheet("saude_docs")

            hoje = datetime.now().strftime("%d/%m/%Y")
            nome_arquivo = f"{hoje}_{descricao_pdf.replace(' ', '_')}"

            sheet.append_row([
                hoje,
                descricao_pdf,
                nome_arquivo,
                link_documento
            ])

            st.success("Documento registrado com sucesso 📄✅")

    st.markdown("---")
    st.subheader("📂 Documentos Registrados")

    client = get_client()
    sheet_docs = client.open("Registro_Atleta_Bernardo").worksheet("saude_docs")
    dados_docs = sheet_docs.get_all_records()

    if not dados_docs:
        st.info("Nenhum documento registrado ainda.")
    else:
        df_docs = pd.DataFrame(dados_docs)

        st.markdown("### 📄 Abrir documentos")

        df_docs["Data_dt"] = pd.to_datetime(df_docs["Data"], dayfirst=True, errors="coerce")
        df_docs = df_docs.sort_values("Data_dt", ascending=False)

        for _, row in df_docs.iterrows():
            if row.get("Link"):
                st.markdown(
                    f"🔗 **{row['Descricao']}**  \n"
                    f"[Abrir PDF]({row['Link']})",
                    unsafe_allow_html=True
                )

    # st.header("🔗 Análises Integradas / Desempenho vs Recuperação")
    # st.markdown(
    #     "Use esta seção para correlacionar o desempenho em jogos com a frequência de treinos e qualidade do sono.")
    #
    #
    # # --- FUNÇÕES HELPER (ASSUMINDO QUE ESTÃO NO ESCOPO GERAL) ---
    # def get_date_obj(date_val):
    #     """Converte a data para objeto datetime, priorizando o formato DD/MM/YYYY."""
    #     return pd.to_datetime(date_val, errors='coerce', dayfirst=True)
    #
    #
    # def get_sleep_date_obj(row):
    #     """
    #     REGRA SIMPLES: Atribui o sono EXATAMENTE à data de despertar ('Data' na planilha).
    #     """
    #     try:
    #         data_acordar = pd.to_datetime(row['Data'], format='%d/%m/%Y', errors='coerce')
    #         if pd.isna(data_acordar):
    #             return pd.NaT
    #         return data_acordar
    #     except:
    #         return pd.NaT
    #
    #
    # # --- FILTRO POR PERÍODO ---
    # periodo_opcoes = {
    #     "Últimos 7 dias": 7,
    #     "Últimas 2 semanas": 14,
    #     "Últimas 4 semanas": 28,
    #     "Últimos 90 dias": 90,
    #     "Todos os Dados": 9999
    # }
    #
    # # --- NOVO: OPÇÕES DE MODALIDADE ---
    # # *AVISO: A linha abaixo pode dar erro se 'load_registros' não estiver no escopo global
    # df_temp_modality = load_registros()
    # modalidades_disponiveis = sorted(
    #     [m for m in df_temp_modality['Condição do Campo'].astype(str).unique()
    #      if m and m.strip() != "" and m.lower() != "nan"])
    # modalidades_opcoes = ["Todas as Modalidades"] + modalidades_disponiveis
    #
    # # --- LAYOUT DOS FILTROS ---
    # col_analise1, col_analise2 = st.columns(2)
    # with col_analise1:
    #     periodo_sel = st.selectbox("Selecione o Período de Análise:", list(periodo_opcoes.keys()))
    # with col_analise2:
    #     modalidade_filter = st.selectbox("Filtrar por Modalidade:", modalidades_opcoes)  # NOVO FILTRO
    #
    # dias_atras = periodo_opcoes[periodo_sel]
    # data_inicial = (datetime.now() - timedelta(days=dias_atras)).replace(hour=0, minute=0, second=0, microsecond=0)
    #
    # st.markdown(f"**Analisando dados desde:** _{data_inicial.strftime('%d/%m/%Y')}_")
    #
    # if st.button("Gerar Análise Integrada"):
    #
    #     # ----------------------------------------------------
    #     # 1. PROCESSAR DADOS DE JOGOS (Gols e Assistências)
    #     # ----------------------------------------------------
    #     df_jogos = load_registros()
    #     # Remove treinos (mantendo apenas jogos)
    #     df_jogos = df_jogos[df_jogos["Treino"].isna() | (df_jogos["Treino"] == "")]
    #
    #     # FILTRA JOGOS USANDO 'Condição do Campo' (CORRETO)
    #     if modalidade_filter != "Todas as Modalidades":
    #         df_jogos = df_jogos[df_jogos["Condição do Campo"].astype(str) == modalidade_filter]
    #
    #     df_jogos["Date_Obj"] = df_jogos["Data"].apply(get_date_obj)
    #     df_jogos_filtrado = df_jogos[df_jogos["Date_Obj"] >= data_inicial].copy()
    #
    #     if df_jogos_filtrado.empty:
    #         df_jogos_group = pd.DataFrame(columns=['Date_Obj', 'Gols Marcados', 'Assistências'])
    #
    #     else:
    #         # Garante que Gols e Assistências são numéricos
    #         def to_int_safe(x):
    #             try:
    #                 return int(x)
    #             except:
    #                 return 0
    #
    #
    #         df_jogos_filtrado["Gols Marcados"] = df_jogos_filtrado["Gols Marcados"].apply(to_int_safe)
    #         df_jogos_filtrado["Assistências"] = df_jogos_filtrado["Assistências"].apply(to_int_safe)
    #
    #         df_jogos_group = df_jogos_filtrado.groupby("Date_Obj")[
    #             ["Gols Marcados", "Assistências"]].sum().reset_index()
    #
    #     # ----------------------------------------------------
    #     # 2. PROCESSAR DADOS DE TREINOS (Contagem Filtrada para Resumo e Geral para Gráfico)
    #     # ----------------------------------------------------
    #     df_treinos = load_treinos_df()
    #     df_treinos["Date_Obj"] = df_treinos["Date"].apply(get_date_obj)
    #     df_treinos_filtrado_geral = df_treinos[df_treinos["Date_Obj"] >= data_inicial].copy()
    #
    #     # Para o Gráfico 2 (Contagem GERAL de treinos no período).
    #     df_treinos_group = df_treinos_filtrado_geral.groupby("Date_Obj").size().reset_index(name='Contagem Treinos')
    #
    #     # --- Lógica de Filtro para o RESUMO Analítico ---
    #     TREINO_MODALIDADE_COL = 'Tipo'  # <<< CORREÇÃO AQUI: USA A COLUNA 'Tipo'
    #     df_treinos_para_resumo = df_treinos_filtrado_geral.copy()
    #
    #     # O filtro de treino só é aplicado se a coluna 'Tipo' existir e o filtro de modalidade estiver ativo
    #     if modalidade_filter != "Todas as Modalidades":
    #         if TREINO_MODALIDADE_COL in df_treinos_para_resumo.columns:
    #             # FILTRA PELA MODALIDADE ESPECÍFICA usando a coluna 'Tipo'
    #             df_treinos_para_resumo = df_treinos_para_resumo[
    #                 df_treinos_para_resumo[TREINO_MODALIDADE_COL].astype(str) == modalidade_filter
    #                 ]
    #             total_treinos_resumo = df_treinos_para_resumo.shape[0]
    #             modalidade_label = modalidade_filter
    #
    #             if total_treinos_resumo == 0:
    #                 # Alerta apenas se o filtro estiver ativo e não houver dados.
    #                 st.warning(
    #                     f"⚠️ **{modalidade_filter}:** Nenhum treino do tipo **{modalidade_filter}** registrado no período. A contagem de treino no resumo será zero.")
    #
    #         else:
    #             # Caso a coluna 'Tipo' não exista na planilha de treinos, o que geraria um KeyError.
    #             total_treinos_resumo = df_treinos_filtrado_geral.shape[0]
    #             modalidade_label = "Total (Coluna Tipo não encontrada no Treino)"
    #             st.error(
    #                 f"❌ **ERRO CRÍTICO:** O DataFrame de Treinos não tem a coluna '{TREINO_MODALIDADE_COL}'. A contagem será GERAL. Revise sua planilha de treinos.")
    #     else:
    #         # Se o filtro é 'Todas as Modalidades', usa a contagem geral.
    #         total_treinos_resumo = df_treinos_filtrado_geral.shape[0]
    #         modalidade_label = "Total Geral"
    #
    #     # Fim da Seção 2
    #     # ----------------------------------------------------
    #
    #     # ----------------------------------------------------
    #     # 3. PROCESSAR DADOS DE SONO (Média de Horas)
    #     # ----------------------------------------------------
    #     df_sono = load_sono_df()
    #     df_sono["Date_Obj"] = df_sono.apply(get_sleep_date_obj, axis=1)
    #     df_sono["Horas Sono"] = df_sono["Duração do Sono (h:min)"].apply(parse_duration_to_hours)
    #     df_sono_filtrado = df_sono[df_sono["Date_Obj"] >= data_inicial].copy()
    #     df_sono_group = df_sono_filtrado.groupby("Date_Obj")['Horas Sono'].mean().reset_index(name='Horas Sono')
    #
    #     # ----------------------------------------------------
    #     # 4. CONSOLIDAR E GERAR GRÁFICO
    #     # ----------------------------------------------------
    #     if (('df_jogos_group' not in locals() or df_jogos_group.empty) and
    #             ('df_treinos_group' not in locals() or df_treinos_group.empty) and
    #             ('df_sono_group' not in locals() or df_sono_group.empty)):
    #         st.warning("Não há dados de Jogo, Treino ou Sono no período selecionado.")
    #     else:
    #
    #         # --- CORREÇÃO CRÍTICA DE NORMALIZAÇÃO DE DATAS ---
    #         # Garante que todas as datas têm hora 00:00:00 para o merge funcionar corretamente
    #         if 'df_jogos_group' in locals() and not df_jogos_group.empty:
    #             df_jogos_group['Date_Obj'] = pd.to_datetime(df_jogos_group['Date_Obj']).dt.normalize()
    #         if 'df_treinos_group' in locals() and not df_treinos_group.empty:
    #             df_treinos_group['Date_Obj'] = pd.to_datetime(df_treinos_group['Date_Obj']).dt.normalize()
    #         if 'df_sono_group' in locals() and not df_sono_group.empty:
    #             df_sono_group['Date_Obj'] = pd.to_datetime(df_sono_group['Date_Obj']).dt.normalize()
    #
    #         # Garante que a coluna Date_Obj usada para merge está normalizada no df_jogos_filtrado
    #         if not df_jogos_filtrado.empty:
    #             df_jogos_filtrado['Date_Obj'] = pd.to_datetime(df_jogos_filtrado['Date_Obj']).dt.normalize()
    #
    #         # Reúne todas as datas disponíveis
    #         all_dates = pd.to_datetime(pd.Series(
    #             (df_jogos_group['Date_Obj'].tolist() if 'df_jogos_group' in locals() else []) +
    #             (df_treinos_group['Date_Obj'].tolist() if 'df_treinos_group' in locals() else []) +
    #             (df_sono_group['Date_Obj'].tolist() if 'df_sono_group' in locals() else [])
    #         ).unique())
    #
    #         if len(all_dates) == 0:
    #             st.warning("Não há dados para plotar.")
    #         else:
    #             # Cria o DataFrame final, AGORA ORDENADO POR DATA CRONOLÓGICA
    #             df_final = pd.DataFrame({'Date_Obj': pd.Series(all_dates).sort_values()})
    #
    #             # FAZ A CONVERSÃO EXPLÍCITA E NOVA ORDENAÇÃO
    #             df_final['Date_Obj'] = pd.to_datetime(df_final['Date_Obj']).dt.normalize()
    #             df_final = df_final.sort_values(by='Date_Obj').reset_index(drop=True)
    #
    #             # Faz a junção (merge) dos 3 datasets
    #             df_final = pd.merge(df_final, df_jogos_group if 'df_jogos_group' in locals() else pd.DataFrame(),
    #                                 on='Date_Obj', how='left')
    #             df_final = pd.merge(df_final, df_treinos_group if 'df_treinos_group' in locals() else pd.DataFrame(),
    #                                 on='Date_Obj', how='left')
    #             df_final = pd.merge(df_final, df_sono_group if 'df_sono_group' in locals() else pd.DataFrame(),
    #                                 on='Date_Obj', how='left')
    #             df_final = df_final.fillna(0)
    #
    #             # REORDENAÇÃO EXPLÍCITA FINAL PÓS-MERGE
    #             df_final = df_final.sort_values(by='Date_Obj').reset_index(drop=True)
    #
    #             # Reagrupar o df_jogos_filtrado por data para obter a contagem de jogos (linhas)
    #             df_contagem_jogos = df_jogos_filtrado.groupby(
    #                 "Date_Obj"
    #             ).size().reset_index(name='Contagem Jogos')
    #
    #             # Merge com df_final para trazer a contagem de jogos para CADA DIA
    #             df_plot = pd.merge(df_final, df_contagem_jogos, on='Date_Obj', how='left').fillna({'Contagem Jogos': 0})
    #             df_plot['Contagem Jogos'] = df_plot['Contagem Jogos'].astype(int)
    #
    #             # GARANTE A ORDEM DO DF_PLOT PELA DATA CORRETA
    #             df_plot = df_plot.sort_values(by='Date_Obj').reset_index(drop=True)
    #
    #             # ----------------------------------------------------------------------
    #             # GRÁFICO 1: DESEMPENHO (Gols e Assistências) - ALTAIR (FINAL FIX)
    #             # ----------------------------------------------------------------------
    #             st.subheader("Gráfico 1: Desempenho (Gols e Assistências)")
    #
    #             # Preparar os dados para o Altair
    #             df_plot['Gols Marcados'] = pd.to_numeric(df_plot['Gols Marcados'], errors='coerce').fillna(0)
    #             df_plot['Assistências'] = pd.to_numeric(df_plot['Assistências'], errors='coerce').fillna(0)
    #
    #             # Filtrar APENAS os dias que tiveram jogos (Contagem Jogos > 0)
    #             df_desempenho_altair = df_plot[df_plot['Contagem Jogos'] > 0].copy()
    #
    #             if df_desempenho_altair.empty:
    #                 st.info("Não há dados de Jogos registrados no período selecionado.")
    #             else:
    #                 # --- PREPARAÇÃO ALTAIR PARA EMPILHAMENTO ---
    #                 df_desempenho_altair['Date_Obj'] = pd.to_datetime(df_desempenho_altair['Date_Obj']).dt.normalize()
    #                 df_desempenho_altair['Data Jogo Formatada'] = df_desempenho_altair['Date_Obj'].dt.strftime('%d/%m')
    #                 df_desempenho_altair = df_desempenho_altair.sort_values(by='Date_Obj').reset_index(drop=True)
    #                 ordered_dates_domain = df_desempenho_altair['Data Jogo Formatada'].unique().tolist()
    #
    #                 # NOVO: Calcula o total de contribuições para a altura da barra e o limite Y
    #                 df_desempenho_altair['Total Contribuicoes'] = df_desempenho_altair['Gols Marcados'] + \
    #                                                               df_desempenho_altair['Assistências']
    #
    #                 # 1. Definição robusta do limite Y
    #                 y_max_data = df_desempenho_altair['Total Contribuicoes'].max() if not df_desempenho_altair[
    #                     'Total Contribuicoes'].empty else 0
    #                 y_max_limit = max(y_max_data + 1.5,
    #                                   3)  # Garante espaço para o rótulo (Nx) e um limite Y mínimo de 3
    #
    #                 # 2. Derreter o DataFrame (Formato longo necessário para barras empilhadas)
    #                 df_melted = df_desempenho_altair.melt(
    #                     id_vars=['Date_Obj', 'Contagem Jogos', 'Data Jogo Formatada', 'Total Contribuicoes'],
    #                     value_vars=['Gols Marcados', 'Assistências'],
    #                     var_name='Métrica',
    #                     value_name='Valor'
    #                 )
    #                 df_melted['Contagem Jogos'] = df_melted['Contagem Jogos'].astype(int)
    #                 chart_title = f"Desempenho em Jogos: Gols e Assistências ({modalidade_filter})"
    #
    #                 # --- CAMADAS DE VISUALIZAÇÃO ---
    #
    #                 # 3. GRÁFICO PRINCIPAL DE BARRAS EMPILHADAS
    #                 chart_bars = alt.Chart(df_melted).mark_bar().encode(
    #                     x=alt.X('Data Jogo Formatada:O',
    #                             axis=alt.Axis(title='Data do Jogo', labelAngle=-45),
    #                             scale=alt.Scale(domain=ordered_dates_domain)),
    #
    #                     # CHAVE PARA EMPILHAMENTO: Usa stack='zero' no Y e configura o eixo
    #                     y=alt.Y('Valor:Q',
    #                             title='Gols / Assistências',
    #                             axis=alt.Axis(format='d', grid=False),  # Sem grade Y para um visual mais limpo
    #                             scale=alt.Scale(domain=[0, y_max_limit]),
    #                             stack="zero"),  # <-- EMPILHADO
    #
    #                     color=alt.Color('Métrica:N',
    #                                     legend=alt.Legend(title="Métrica"),
    #                                     scale=alt.Scale(domain=['Gols Marcados', 'Assistências'],
    #                                                     range=['#E45757', '#FF8C00'])),
    #                     order=alt.Order('Métrica', sort='descending'),
    #                     # Gols (vermelho) no topo, Assistências (laranja) na base
    #                     tooltip=[
    #                         alt.Tooltip('Date_Obj:T', title='Data Completa', format='%d/%m/%Y'),
    #                         alt.Tooltip('Métrica:N', title='Métrica'),
    #                         alt.Tooltip('Valor:Q', title='Quantidade', format='.0f'),
    #                         alt.Tooltip('Contagem Jogos:Q', title='Nº de Jogos no Dia')
    #                     ]
    #                 ).properties(
    #                     title=chart_title
    #                 )
    #
    #                 # 4. RÓTULOS DE TEXTO (Gols e Assistências) - Centralização Otimizada
    #
    #                 # Camada de Texto para GOLS (Vermelho - Topo)
    #                 text_gols_layer = alt.Chart(df_melted).mark_text(
    #                     align='center',
    #                     baseline='middle',
    #                     color='white',  # COR BRANCA (Contraste)
    #                     fontWeight='bold',
    #                     dy=15  # AUMENTADO: Move para baixo no segmento vermelho (centralização)
    #                 ).encode(
    #                     x='Data Jogo Formatada:O',
    #                     y=alt.Y('Valor:Q', stack='zero'),
    #                     text=alt.Text('Valor:Q', format='.0f'),
    #                     # Só mostra se for Gol e o Valor for >= 1
    #                     opacity=alt.condition((alt.datum.Métrica == 'Gols Marcados') & (alt.datum.Valor >= 1),
    #                                           alt.value(1), alt.value(0))
    #                 )
    #
    #                 # Camada de Texto para ASSISTÊNCIAS (Laranja - Base)
    #                 text_assistencias_layer = alt.Chart(df_melted).mark_text(
    #                     align='center',
    #                     baseline='middle',
    #                     color='white',  # COR BRANCA (Contraste)
    #                     fontWeight='bold',
    #                     dy=14  # AUMENTADO: Move para cima no segmento laranja (centralização)
    #                 ).encode(
    #                     x='Data Jogo Formatada:O',
    #                     y=alt.Y('Valor:Q', stack='zero'),
    #                     text=alt.Text('Valor:Q', format='.0f'),
    #                     # Só mostra se for Assistência e o Valor for >= 1
    #                     opacity=alt.condition((alt.datum.Métrica == 'Assistências') & (alt.datum.Valor >= 1),
    #                                           alt.value(1), alt.value(0))
    #                 )
    #
    #                 # 5. RÓTULOS (Nx) - Contagem de Jogos (Acima da Barra)
    #                 df_multi_jogos_labels = df_desempenho_altair.copy()
    #                 df_multi_jogos_labels['Label'] = '(' + df_multi_jogos_labels['Contagem Jogos'].astype(str) + 'x)'
    #                 # Agora ValorMax usa o Total Contribuicoes (topo da barra empilhada)
    #                 df_multi_jogos_labels['ValorMax'] = df_multi_jogos_labels['Total Contribuicoes']
    #
    #                 text_layer_nx = alt.Chart(df_multi_jogos_labels).mark_text(
    #                     align='center',
    #                     baseline='bottom',
    #                     dy=-5,  # Pouco acima do topo da barra
    #                     color='blue',
    #                     fontWeight='bold'
    #                 ).encode(
    #                     x='Data Jogo Formatada:O',
    #                     y=alt.Y('ValorMax:Q', stack=None, axis=None),
    #                     text=alt.Text('Label:N'),
    #                     order=alt.Order('Date_Obj', sort='ascending'),
    #                     opacity=alt.condition(alt.datum['Contagem Jogos'] > 0, alt.value(1), alt.value(0))
    #                 )
    #
    #                 # 6. COMBINAÇÃO FINAL
    #                 final_chart = chart_bars + text_gols_layer + text_assistencias_layer + text_layer_nx
    #
    #                 st.markdown("<p style='font-size:12px; color:blue; margin-bottom: 0;'>\
    #                                                                     🟦 indica o número de jogos disputados no dia.<br>\
    #                                                                     **Rótulos brancos:** Não consta Gols/Assistencias.</p>",
    #                             unsafe_allow_html=True)
    #
    #                 st.altair_chart(final_chart, use_container_width=True)
    #             # ----------------------------------------------------
    #             # GRÁFICO 2: RECUPERAÇÃO E FREQUÊNCIA (SONO E TREINOS) - MATPLOTLIB
    #             # ----------------------------------------------------
    #
    #             st.subheader("Gráfico 2: Recuperação e Frequência (Sono e Treinos)")
    #
    #             # O df_final já está ordenado nesta etapa (na Seção 4)
    #             x_labels_full = df_final['Date_Obj'].dt.strftime('%d/%m')
    #             x_indices_full = np.arange(len(x_labels_full))
    #
    #             # O restante do Gráfico 2 segue inalterado.
    #             # ...
    #
    #             # --- GRÁFICO 2: SONO (Eixo 1) E TREINOS (Eixo 2) ---
    #             fig2, ax2 = plt.subplots(figsize=(14, 5))
    #
    #             # Eixo 1: SONO
    #             ax2.plot(x_indices_full, df_final['Horas Sono'], label='Média Horas Sono', color='tab:green',
    #                      marker='o',
    #                      linestyle='-', linewidth=2)
    #             ax2.set_ylabel('Horas de Sono', color='tab:green')
    #             ax2.tick_params(axis='y', labelcolor='tab:green')
    #             ax2.set_ylim(0, 12)  # CORREÇÃO: Aumenta o limite para evitar corte no valor máximo (10.0)
    #
    #             # Eixo 2: TREINOS
    #             ax3 = ax2.twinx()
    #             ax3.plot(x_indices_full, df_final['Contagem Treinos'], label='Contagem Treinos', color='tab:blue',
    #                      marker='o', linestyle='-', linewidth=2)
    #             ax3.set_ylabel('Contagem Treinos', color='tab:blue')
    #             ax3.tick_params(axis='y', labelcolor='tab:blue')
    #             ax3.set_ylim(bottom=0, top=df_final['Contagem Treinos'].max() * 1.5 + 1)
    #
    #             # Rótulos de Sono e Treinos
    #             for i, txt in enumerate(df_final['Horas Sono']):
    #                 if txt > 0:
    #                     ax2.annotate(f'{txt:.1f}', (x_indices_full[i], df_final['Horas Sono'][i]),
    #                                  textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10,
    #                                  color='tab:green', fontweight='bold')
    #             for i, txt in enumerate(df_final['Contagem Treinos']):
    #                 if txt > 0:
    #                     ax3.annotate(f'{int(txt)}', (x_indices_full[i], df_final['Contagem Treinos'][i]),
    #                                  textcoords="offset points", xytext=(0, -15), ha='center', fontsize=10,
    #                                  color='tab:blue', fontweight='bold')
    #
    #             # Configuração do Eixo X
    #             ax2.set_xticks(x_indices_full)
    #             ax2.set_xticklabels(x_labels_full, rotation=45, ha='right')
    #             ax2.set_xlabel("Data")
    #             plt.grid(axis='y', linestyle='--', alpha=0.6)
    #
    #             lines, labels = ax2.get_legend_handles_labels()
    #             lines3, labels3 = ax3.get_legend_handles_labels()
    #             ax2.legend(lines + lines3, labels + labels3, loc='upper left')
    #
    #             st.pyplot(fig2)
    #
    #             #----------------------------------------------------------------
    #
    #
    #
    #             # ----------------------------------------------------
    #             # 5. RESUMO E DIAGNÓSTICO DE FOCO
    #             # ----------------------------------------------------
    #             st.subheader("📊 Resumo Analítico e Foco da Semana")
    #
    #             # CÁLCULOS CHAVE
    #             total_gols = df_final['Gols Marcados'].sum()
    #             total_assistencias = df_final['Assistências'].sum()
    #             # A contagem de dias_com_jogo (registros) foi corrigida no código anterior, mantida aqui.
    #             dias_com_jogo = df_jogos_filtrado.shape[0]
    #             dias_unicos_com_jogo = df_final[
    #                 (df_final['Gols Marcados'] > 0) | (df_final['Assistências'] > 0)
    #                 ].shape[0]
    #
    #             if dias_unicos_com_jogo == 0 and 'df_jogos_group' in locals() and not df_jogos_group.empty:
    #                 dias_unicos_com_jogo = df_jogos_group.shape[0]
    #
    #             divisor_media = dias_unicos_com_jogo if dias_unicos_com_jogo > 0 else 1
    #
    #             media_gols_por_jogo = total_gols / divisor_media
    #             media_assistencias_por_jogo = total_assistencias / divisor_media
    #
    #             # Média Geral de Recuperação
    #             media_sono = df_final[df_final['Horas Sono'] > 0]['Horas Sono'].mean()
    #
    #             # total_treinos_resumo e modalidade_label já foram calculados corretamente na Seção 2.
    #
    #             # PARÂMETROS DE REFERÊNCIA
    #             REF_SONO_MINIMO = 8.0
    #             REF_TREINO_MINIMO = 2
    #
    #             # --------------------------------------------------------
    #             # LÓGICA DE TEXTO PARA O RESUMO
    #             # --------------------------------------------------------
    #
    #             # Gera o texto de análise da frequência
    #             if total_treinos_resumo > 0:
    #                 frequencia_analise_texto = (
    #                     f"A frequência de treino (**{modalidade_label}**) foi **{'alta' if total_treinos_resumo >= REF_TREINO_MINIMO else 'baixa'}**, "
    #                     f"com **{total_treinos_resumo} sessões** no período. Foco em manter a consistência."
    #                 )
    #             else:
    #                 frequencia_analise_texto = f"Nenhum treino de **{modalidade_label}** registrado no período."
    #
    #             # --- ANÁLISE GERAL ---
    #             analise_texto = []
    #
    #             # 1. ANÁLISE DE DESEMPENHO (GOLS E ASSISTÊNCIAS)
    #             if total_gols > 0 or total_assistencias > 0:
    #                 analise_texto.append(
    #                     f"1. ANÁLISE DE DESEMPENHO: O desempenho em jogos ({modalidade_filter}) foi de **{total_gols} Gols** e **{total_assistencias} Assistências** no total, "
    #                     f"com média de **{media_gols_por_jogo:.1f} Gols/Jogo** e **{media_assistencias_por_jogo:.1f} Assis./Jogo** nos {dias_com_jogo} jogos registrados.")
    #             else:
    #                 analise_texto.append(
    #                     f"1. ANÁLISE DE DESEMPENHO: Não houve Gols ou Assistências registradas nos jogos ({modalidade_filter}) do período.")
    #
    #             # 2. ANÁLISE DE SONO/RECUPERAÇÃO (Mantida)
    #             if pd.notna(media_sono):
    #                 if media_sono >= REF_SONO_MINIMO:
    #                     analise_texto.append(
    #                         f"2. ANÁLISE DE SONO: A recuperação foi **excelente**: média de **{media_sono:.1f} horas de sono**, acima da meta de {REF_SONO_MINIMO}h. Isso sugere boa base de energia.")
    #                 elif media_sono >= (REF_SONO_MINIMO - 0.5):
    #                     analise_texto.append(
    #                         f"2. ANÁLISE DE SONO: A recuperação foi **boa**: média de **{media_sono:.1f} horas de sono**. Manteve-se próximo do ideal ({REF_SONO_MINIMO}h).")
    #                 else:
    #                     analise_texto.append(
    #                         f"2. ANÁLISE DE SONO: 🚨 **ALERTA DE FADIGA:** A média de sono foi de apenas **{media_sono:.1f} horas**. Esse déficit pode impactar negativamente a performance e o risco de lesões.")
    #             else:
    #                 analise_texto.append("2. ANÁLISE DE SONO: Dados de sono insuficientes para análise de recuperação.")
    #
    #             # 3. ANÁLISE DE FREQUÊNCIA DE TREINO (USA O TEXTO CORRIGIDO)
    #             analise_texto.append(f"3. ANÁLISE DE FREQUÊNCIA DE TREINO: {frequencia_analise_texto}")
    #
    #             # --- CONCLUSÃO E FOCO ---
    #             st.markdown("---")
    #             st.markdown("#### Conclusão da Semana:")
    #
    #             # ATUALIZAÇÃO DO RESUMO: Usa total_treinos_resumo e modalidade_label
    #             resumo_texto = f"""
    #                                                                        **Resumo do Período Pesquisado:**
    #
    #                                                                        - **Jogos Registrados ({modalidade_filter}):** {dias_com_jogo}
    #                                                                        - **Gols Marcados:** {int(total_gols)}
    #                                                                        - **Assistências:** {int(total_assistencias)}
    #                                                                        - **Sessões de Treino ({modalidade_label}):** {int(total_treinos_resumo)}
    #                                                                        - **Média de Sono:** {media_sono:.1f} horas
    #                                                                        """
    #             st.info(resumo_texto)
    #
    #             # Lógica para conclusão (usando GOLS/ASSISTENCIAS > 0)
    #             desempenho_positivo = total_gols > 0 or total_assistencias > 0
    #
    #             # A lógica de conclusão também deve usar o total_treinos_resumo
    #             if desempenho_positivo and media_sono >= REF_SONO_MINIMO and total_treinos_resumo > 0:
    #                 st.success(
    #                     "✅ **Ótimo Equilíbrio!** O alto desempenho (Gols e Assistências) está correlacionado com a excelente recuperação (Sono) e boa frequência de treino. FOCO: Manter este padrão.")
    #
    #             elif media_sono < REF_SONO_MINIMO and desempenho_positivo:
    #                 st.warning(
    #                     "⚠️ **Rendimento em Risco!** Apesar do desempenho ofensivo (Gols/Assistências), a baixa média de sono pode indicar que o corpo está sendo exigido além da conta. FOCO: Priorizar o descanso imediatamente.")
    #
    #             elif media_sono < REF_SONO_MINIMO and not desempenho_positivo:
    #                 media_sono_formatada = f"{media_sono:.1f}"
    #                 st.error(
    #                     f"❌ **Alerta Geral!** Baixo rendimento (sem Gols/Assistências) combinado com sono insuficiente (média de **{media_sono_formatada} horas**). O foco principal deve ser a **Recuperação e o Sono** para restaurar a energia.")
    #
    #             # ----------------------------------------------------
    #             # 5.1. TABELA DE DETALHES DE GOLS POR ADVERSÁRIO (AJUSTADA E REORDENADA)
    #             # ----------------------------------------------------
    #             if total_gols > 0 or total_assistencias > 0:
    #                 st.subheader("🎯 Detalhe do Desempenho Ofensivo")
    #
    #                 df_gols_filtrado = df_jogos_filtrado[
    #                     (df_jogos_filtrado['Gols Marcados'] > 0) |
    #                     (df_jogos_filtrado['Assistências'] > 0)
    #                     ].copy()
    #
    #                 if not df_gols_filtrado.empty:
    #
    #                     # 2. Agrupa e calcula as colunas (Sintaxe de agg MAIS COMPATÍVEL)
    #                     df_resumo_adversario = df_gols_filtrado.groupby('Visitante').agg(
    #                         Gols=('Gols Marcados', 'sum'),
    #                         Assistencias=('Assistências', 'sum'),
    #                         Jogos=('Visitante', 'size'),
    #                         # Pega a Data mais recente como um objeto DATETIME para ordenação correta
    #                         Ultimo_Jogo_Raw=('Date_Obj', 'max')
    #                     ).reset_index()
    #
    #                     # 3. Formata e Renomeia para exibição
    #                     df_resumo_adversario = df_resumo_adversario.rename(columns={
    #                         'Visitante': 'Adversário',
    #                         'Gols': 'Total Gols',
    #                         'Assistencias': 'Total Assistências',
    #                         'Jogos': 'Nº de Jogos',
    #                     })
    #
    #                     # 4. ORDENAÇÃO: ORDENA APENAS PELA DATA (MAIS RECENTE PARA MAIS ANTIGA)
    #                     df_resumo_adversario = df_resumo_adversario.sort_values(
    #                         by=['Ultimo_Jogo_Raw'],  # Lista contém APENAS a coluna de Data (objeto datetime)
    #                         # False = Decrescente (do mais recente para o mais antigo)
    #                         ascending=[False]
    #                     )
    #
    #                     # 5. FORMATAÇÃO FINAL: Mapeia o objeto de data para a coluna final e formata para string (somente para exibição)
    #                     df_resumo_adversario['Último Jogo'] = pd.to_datetime(
    #                         df_resumo_adversario['Ultimo_Jogo_Raw']
    #                     ).dt.strftime('%d/%m/%Y')
    #
    #                     # Remove a coluna temporária usada na ordenação
    #                     df_resumo_adversario = df_resumo_adversario.drop(columns=['Ultimo_Jogo_Raw'])
    #
    #                     st.markdown(f"#### Gols e Assistências Contra Adversários ({modalidade_filter})")
    #
    #                     # NOVO: Define a ORDEM DAS COLUNAS SOLICITADA
    #                     colunas_ordenadas = [
    #                         'Último Jogo',
    #                         'Adversário',
    #                         'Total Gols',
    #                         'Total Assistências',
    #                         'Nº de Jogos'
    #                     ]
    #
    #                     # Exibe apenas as colunas solicitadas
    #                     st.dataframe(
    #                         df_resumo_adversario[colunas_ordenadas],
    #                         hide_index=True,
    #                         use_container_width=True
    #                     )
    #                 else:
    #                     st.info(
    #                         f"Nenhum Adversário resultou em Gols ou Assistências em {modalidade_filter} neste período.")

#-------------------------------------
# Aba Campeonatos BLOCO: LOGOS DOS CAMPEONATOS (AGORA DENTRO DA NOVA ABA)
# ----------------------------------------------------------------------
if st.session_state["pagina"] == "campeonatos":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    # --- NOVO BLOCO: CSS ESPECÍFICO PARA CENTRALIZAR O LOGO E O LINK ---
    st.markdown("""
            <style>
            /* Centraliza o cabeçalho (H1/H2) da aba */
            [data-testid="stHeader"] h1,
            [data-testid="stMarkdownContainer"] h1,
            [data-testid="stMarkdownContainer"] h2,
            [data-testid="stHeader"] {
                text-align: center;
                width: 100%; /* Garante que o container ocupe toda a largura */
            }

            /* Regra específica para centralizar o st.header */
            [data-testid="stHeader"] > div > div:nth-child(1) {
                justify-content: center;
            }

            /* Centraliza o texto normal (o subtítulo "Acesse as tabelas...") */
            [data-testid="stMarkdownContainer"] p {
                 text-align: center;
                 width: 100%;
            }
            </style>
        """, unsafe_allow_html=True)
    # FIM DO NOVO BLOCO CSS
#--------------------------------------------------

    st.header("🏆 Acesso Rápido aos Campeonatos")
    st.markdown("Acesse as tabelas e resultados oficiais das competições:")

    # --- ESPAÇAMENTO PARA AFASTAR DO PRIMEIRO LOGO ---
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------
    # Se você tem muitos logos, use uma coluna maior (ex: 3 colunas) para que não quebre no celular
    col_logo1, col_logo2, col_logo3, col_logo4 = st.columns(4)
    col_logo5, col_logo6, col_logo7, col_logo8 = st.columns(4)
    # ---------------------------------------------

    TAMANHO_LOGO = 80  # Define o tamanho padrão

    # Linha 1 de logos (4 colunas)
    criar_logo_link_alinhado(col_logo1, LOGO_PATH_1, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo2, LOGO_PATH_2, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo3, LOGO_PATH_3, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo4, LOGO_PATH_4, TAMANHO_LOGO)

    st.markdown("---")  # Separador visual

    # Linha 2 de logos (4 colunas)
    criar_logo_link_alinhado(col_logo5, LOGO_PATH_5, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo6, LOGO_PATH_6, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo7, LOGO_PATH_7, TAMANHO_LOGO)
    criar_logo_link_alinhado(col_logo8, LOGO_PATH_8, TAMANHO_LOGO)

def parse_duration_to_hours(dur_str):
    """Converte a duração de sono (ex: '7:30', '7:30:00') em horas decimais (ex: 7.5)."""
    try:
        parts = str(dur_str).split(":")
        if len(parts) >= 2:
            hours = float(parts[0])
            minutes = float(parts[1])
            return hours + (minutes / 60)
        return float(dur_str) if pd.notna(dur_str) else 0.0
    except:
        return 0.0

def filter_df_by_date(df, date_col, start_date, end_date):
    """Filtra o DataFrame por um período de data, tratando a data como string DD/MM/YYYY."""
    try:
        df_temp = df.copy()
        date_format = '%d/%m/%Y'
        # Garante que a coluna de data é string antes da conversão para evitar ArrowTypeError
        df_temp[date_col] = df_temp[date_col].astype(str)

        df_temp['Data_DT'] = pd.to_datetime(df_temp[date_col], format=date_format, errors='coerce', dayfirst=True)

        df_temp = df_temp.dropna(subset=['Data_DT'])

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        df_filtrado = df_temp[
            (df_temp['Data_DT'] >= start_dt) &
            (df_temp['Data_DT'] <= end_dt)
            ]
        return df_filtrado
    except Exception as e:
        # st.error(f"Erro ao filtrar dados por data: {e}")
        return pd.DataFrame(columns=df.columns)

def safe_sum(series):
    return pd.to_numeric(series, errors='coerce').fillna(0).sum()

def calculate_metrics(df_jogos, df_treinos, df_sono):
    """Calcula todas as métricas para os cards."""

    total_jogos = len(df_jogos)
    total_gols = int(safe_sum(df_jogos['Gols Marcados']))
    total_assistencias = int(safe_sum(df_jogos['Assistências']))
    total_minutos = int(safe_sum(df_jogos['Minutos Jogados']))

    total_treinos = len(df_treinos)

    if not df_sono.empty and 'Duração do Sono (h:min)' in df_sono.columns:
        df_sono['Duração_Horas'] = df_sono['Duração do Sono (h:min)'].apply(parse_duration_to_hours)
        media_sono_decimal = df_sono['Duração_Horas'].mean() if len(df_sono) > 0 else 0.0
    else:
        media_sono_decimal = 0.0

    horas = int(media_sono_decimal)
    minutos = int((media_sono_decimal - horas) * 60)
    media_sono_formatada = f"{horas}h{minutos:02d}m"

    return total_jogos, total_gols, total_assistencias, total_minutos, total_treinos, media_sono_formatada, media_sono_decimal

def analisar_resultado(df):
    """Calcula o total de Vitórias, Empates e Derrotas com base na coluna 'Resultado'."""
    vitorias, empates, derrotas = 0, 0, 0
    total_jogos = len(df)

    if total_jogos == 0 or 'Resultado' not in df.columns:
        return 0, 0, 0, 0

    for resultado_str in df['Resultado'].astype(str):
        if pd.isna(resultado_str) or 'x' not in resultado_str:
            continue
        try:
            gols_atleta = int(resultado_str.split('x')[0].strip())
            gols_adversario = int(resultado_str.split('x')[1].strip())

            if gols_atleta > gols_adversario:
                vitorias += 1
            elif gols_atleta == gols_adversario:
                empates += 1
            else:
                derrotas += 1
        except ValueError:
            continue

    return total_jogos, vitorias, empates, derrotas


def calculate_avaliacao_tecnica(df_jogos_f, modalidade_filter, time_filter):
    """
    Calcula a Avaliação Técnica (índice ponderado) e gera uma conclusão explicativa.
    Retorna: (nota_formatada, conclusao_texto)
    """

    if df_jogos_f.empty:
        return "N/A", "Não há dados de jogos para o período/filtros selecionados."

    # 1. PARAMETROS DE BASE POR MODALIDADE (Ajuste conforme o nível esperado)
    modalidade = modalidade_filter.lower()

    # Bases Futsal (Mais gols, menos minutos por jogo)
    if 'futsal' in modalidade:
        BASE_GOLS_POR_JOGO = 0.80
        BASE_ASSISTENCIAS_POR_JOGO = 0.30
        BASE_MINUTAGEM_POR_JOGO = 15  # Em minutos por jogo
        PESO_GOLS = 0.45  # Mais foco em gols no futsal
        PESO_ASSISTENCIAS = 0.25
        PESO_MINUTAGEM = 0.20
        PESO_VITORIAS = 0.10

    # Bases Campo (Menos gols, mais minutos por jogo)
    elif 'campo' in modalidade:
        BASE_GOLS_POR_JOGO = 0.50
        BASE_ASSISTENCIAS_POR_JOGO = 0.20
        BASE_MINUTAGEM_POR_JOGO = 30  # Em minutos por jogo
        PESO_GOLS = 0.40
        PESO_ASSISTENCIAS = 0.20
        PESO_MINUTAGEM = 0.30
        PESO_VITORIAS = 0.10

    # Bases Padrão/Outros (Fallback)
    else:
        BASE_GOLS_POR_JOGO = 0.50
        BASE_ASSISTENCIAS_POR_JOGO = 0.20
        BASE_MINUTAGEM_POR_JOGO = 20
        PESO_GOLS = 0.35
        PESO_ASSISTENCIAS = 0.25
        PESO_MINUTAGEM = 0.30
        PESO_VITORIAS = 0.10

    # 2. OBTENÇÃO DOS VALORES
    total_jogos = len(df_jogos_f)
    total_gols = safe_sum(df_jogos_f['Gols Marcados'])
    total_assistencias = safe_sum(df_jogos_f['Assistências'])
    total_minutagem = safe_sum(df_jogos_f['Minutos Jogados'])

    # Calculo da % de vitórias
    total_jogos_vd, vitorias_vd, _, _ = analisar_resultado(df_jogos_f)
    vitorias_percent = (vitorias_vd / total_jogos_vd) if total_jogos_vd > 0 else 0.0

    # 3. CÁLCULO E NORMALIZAÇÃO DAS MÉTRICAS
    gols_por_jogo = total_gols / total_jogos
    assistencias_por_jogo = total_assistencias / total_jogos
    minutagem_por_jogo = total_minutagem / total_jogos

    # Usamos min() para limitar o score a um valor máximo (ex: 1.5) para evitar notas muito distorcidas
    score_gols = min(gols_por_jogo / BASE_GOLS_POR_JOGO, 1.5)
    score_assistencias = min(assistencias_por_jogo / BASE_ASSISTENCIAS_POR_JOGO, 1.5)
    score_minutagem = min(minutagem_por_jogo / BASE_MINUTAGEM_POR_JOGO, 1.5)
    score_vitorias = vitorias_percent

    # 4. CÁLCULO PONDERADO
    nota_ponderada = (
            (PESO_GOLS * score_gols) +
            (PESO_ASSISTENCIAS * score_assistencias) +
            (PESO_MINUTAGEM * score_minutagem) +
            (PESO_VITORIAS * score_vitorias)
    )

    nota_final = min(nota_ponderada * 10, 10.0)

    # 5. GERAÇÃO DA CONCLUSÃO (LÓGICA DO TEXTO)

    # a. Identifica o foco
    foco = time_filter if time_filter != "Todos" else modalidade_filter

    # b. Encontra o Ponto Forte (Score > 1.0 ou Score mais alto)
    scores = {'Gols': score_gols, 'Assistências': score_assistencias, 'Minutagem': score_minutagem}
    ponto_forte_key = max(scores, key=scores.get)
    ponto_forte_score = scores[ponto_forte_key]

    # c. Encontra o Ponto a Desenvolver (Score mais baixo)
    ponto_desenvolver_key = min(scores, key=scores.get)
    ponto_desenvolver_score = scores[ponto_desenvolver_key]

    # d. Monta a Conclusão

    if nota_final >= 9.0:
        texto_inicial = "Excelente Performance!"
        texto_principal = f"O atleta demonstrou um desempenho de altíssimo nível em {foco}. Sua nota é impulsionada pela excelência em **{ponto_forte_key}** (Score: {ponto_forte_score:.2f})."
    elif nota_final >= 7.0:
        texto_inicial = "Boa Performance Geral."
        texto_principal = f"O desempenho em {foco} é sólido. O ponto forte está em **{ponto_forte_key}** (Score: {ponto_forte_score:.2f}), mas há espaço para crescimento, especialmente em **{ponto_desenvolver_key}** (Score: {ponto_desenvolver_score:.2f})."
    elif nota_final >= 5.0:
        texto_inicial = "Performance Moderada."
        texto_principal = f"A performance em {foco} é mediana. A contribuição ofensiva e a minutagem precisam ser ajustadas, com o ponto mais fraco em **{ponto_desenvolver_key}** (Score: {ponto_desenvolver_score:.2f})."
    else:
        texto_inicial = "Atenção Necessária."
        texto_principal = f"O desempenho em {foco} está abaixo do esperado. O fator que mais puxa a nota para baixo é **{ponto_desenvolver_key}** (Score: {ponto_desenvolver_score:.2f}), indicando necessidade de foco urgente nesta área."

    conclusao_texto = f"**{texto_inicial}** A nota ({nota_final:.1f}) reflete: {texto_principal}"

    return f"{nota_final:.1f}", conclusao_texto

def calculate_engajamento(df_treinos_f, df_sono_f, total_dias_periodo, media_sono_decimal):
    """Calcula o Engajamento baseado em Treinos (Presença) e Sono (Qualidade)."""

    # 1. PARAMETROS E PESOS
    PESO_TREINO = 0.5
    PESO_SONO = 0.5
    META_SONO_DIARIO = 7.0  # Exemplo: 7 horas é a meta
    TREINOS_ESPERADOS = 15  # Exemplo: 15 treinos esperados no período

    # 2. CÁLCULO DE ADERÊNCIA AO TREINO (Disciplina)
    total_treinos_realizados = len(df_treinos_f)

    # Se não houver treinos no período, assume 100% (ou 0%) dependendo da regra do clube.
    # Vamos assumir 100% para não penalizar se não houver treinos agendados.
    if TREINOS_ESPERADOS == 0:
        score_treino = 100.0
    else:
        # Calcula a porcentagem de treinos feitos
        score_treino = min(100.0, (total_treinos_realizados / TREINOS_ESPERADOS) * 100.0)

    # 3. CÁLCULO DE QUALIDADE DO SONO (Saúde)

    # Penalidade de sono:
    # Se a média de sono estiver abaixo da meta, o score cai.
    if total_dias_periodo > 0 and media_sono_decimal > 0.0:
        # Penaliza se a média estiver abaixo da meta (7.0h)
        if media_sono_decimal < META_SONO_DIARIO:
            # Penalidade proporcional:
            # Ex: Se a meta é 7h e a média é 6h (desvio de 1h), score cai 10%.
            desvio_percentual = (META_SONO_DIARIO - media_sono_decimal) / META_SONO_DIARIO
            score_sono = max(0.0, 100.0 - (desvio_percentual * 100.0))
        else:
            score_sono = 100.0  # Bônus se a média for igual ou superior à meta
    else:
        score_sono = 100.0  # Não penaliza se não houver dados de sono

    # 4. CÁLCULO FINAL PONDERADO

    engajamento_ponderado = (score_treino * PESO_TREINO) + (score_sono * PESO_SONO)

    return f"{engajamento_ponderado:.0f}%"

# --------------------------------------------------------------------------
# 0. CONFIGURAÇÃO DE ESTILO (CSS - TEMA ESCURO E CARDS PERSONALIZADOS)
# --------------------------------------------------------------------------
def inject_custom_css():
    st.markdown(
        f"""
        <style>
        /* 2. Estilo Base dos Cards */
        .card-jogos, .card-gols, .card-assistencias, 
        .card-minutos, .card-treinos, .card-sono, .card-derrotas,
        .card-vitorias, .card-avaliacao, .card-engajamento, .card-modalidade, .card-media-gols {{
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.5); 
            transition: 0.3s;
            color: white; 
            margin-bottom: 10px; 
            height: 100%; 
            text-align: left; 
            font-size: 1em; 
            line-height: 1.2; 
        }}

        /* 3. Estilo dos Títulos (o texto em negrito com o ícone) */
        .card-jogos strong, .card-gols strong, .card-assistencias strong,
        .card-minutos strong, .card-treinos strong, .card-sono strong,
        .card-derrotas strong, .card-vitorias strong, .card-avaliacao strong,
        .card-engajamento strong, .card-modalidade strong, .card-media-gols strong {{
            font-size: 1.1em; 
            color: white;
            display: block; 
            margin-bottom: 0.5em; 
        }}

        /* 4. Estilo dos valores principais (o NÚMERO GRANDE) */
        .card-jogos p, .card-gols p, .card-assistencias p, 
        .card-minutos p, .card-treinos p, .card-sono p, 
        .card-derrotas p, .card-vitorias p, .card-avaliacao p,
        .card-engajamento p, .card-modalidade p, .card-media-gols p {{
            font-size: 2.2em; /* Aumentado o tamanho da fonte */
            font-weight: bold; /* Garante que seja negrito */
            margin: 0.1em 0; 
            color: white; 
            text-align: center; /* Centraliza o número */
            line-height: 1.1; /* Ajuste para espaçamento vertical */
        }}

        /* 5. Estilo do rótulo/subtexto (o texto cinza pequeno da segunda linha) */
        .card-jogos label, .card-gols label, .card-assistencias label, 
        .card-minutos label, .card-treinos label, .card-sono label,
        .card-derrotas label, .card-vitorias label, .card-avaliacao label,
        .card-engajamento label, .card-modalidade label, .card-media-gols label {{
            font-size: 0.75em; 
            font-weight: normal;
            color: rgba(255, 255, 255, 0.7); 
            display: block; 
            margin-top: 0.1em; 
            text-align: center; /* Centraliza o subtexto também para consistência */
        }}

        /* 6. Cores Individuais para os Cards (FUNDO COMPLETO) */
        .card-jogos {{ background-color: #00BCD4; }}
        .card-gols {{ background-color: #4CAF50; }}
        .card-assistencias {{ background-color: #FF9800; }}
        .card-minutos {{ background-color: #2196F3; }}
        .card-treinos {{ background-color: #9C27B0; }}
        .card-sono {{ background-color: #009688; }}
        .card-derrotas {{ background-color: #C62828; }} /* Vermelho Escuro */
        .card-vitorias {{ background-color: #009688; }} /* Verde Água (Igual ao sono, se preferir outra cor, ajuste) */
        .card-avaliacao {{ background-color: #9C27B0; }} /* Roxo (Igual ao treinos, se preferir outra cor, ajuste) */
        .card-engajamento {{ background-color: #2196F3; }} /* Azul Escuro (Igual ao minutos, se preferir outra cor, ajuste) */
        .card-modalidade {{ background-color: #00BCD4; }} /* Azul Claro (Igual ao jogos, se preferir outra cor, ajuste) */
        .card-media-gols {{ background-color: #4CAF50; }} /* Verde Claro (Igual ao gols, se preferir outra cor, ajuste) */

        /* 7. Estilo dos títulos dos gráficos e outros textos no Dark Mode */
        h3 {{ color: #E0E0E0; }}

        /* Otimização de Margens - Remove as margens do p e label dentro do div, deixando o controle para o CSS acima */
        .card-jogos > p, .card-gols > p, .card-assistencias > p, 
        .card-minutos > p, .card-treinos > p, .card-sono > p,
        .card-derrotas > p, .card-vitorias > p, .card-avaliacao > p,
        .card-engajamento > p, .card-modalidade > p, .card-media-gols > p {{
            margin-bottom: 0;
            margin-top: 0;
        }}
        .card-jogos > label, .card-gols > label, .card-assistencias > label, 
        .card-minutos > label, .card-treinos > label, .card-sono > label,
        .card-derrotas > label, .card-vitorias > label, .card-avaliacao > label,
        .card-engajamento > label, .card-modalidade > label, .card-media-gols > label {{
            margin-top: 0;
            margin-bottom: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
# Chamar o CSS antes de construir a tab (se for chamado dentro do with tab[5], só afetará essa tab)
# Se você tiver um bloco de setup no topo do seu script, chame lá para afetar toda a aplicação.
inject_custom_css()

# --------------------------------------------------------------------------
# INÍCIO DO CÓDIGO DENTRO DO with tab[5] - DASHBOARD

st.markdown("""
<style>
.scout-card {
    border-radius: 18px;
    padding: 18px;
    text-align: center;
    color: white;
    box-shadow: 0 6px 18px rgba(0,0,0,0.45);
    height: 100%;
}

.scout-title {
    font-size: 14px;
    opacity: 0.85;
}

.scout-value {
    font-size: 42px;
    font-weight: bold;
    margin-top: 6px;
}

/* === MESMAS CORES DO GRÁFICO === */

.bg-chutes {
    background: linear-gradient(135deg, #00E5FF, #0288D1);
}

.bg-chutes-errados {
    background: linear-gradient(135deg, #FF1744, #B71C1C);
}

.bg-passes {
    background: linear-gradient(135deg, #00E676, #2E7D32);
}


.bg-passes-errados {
    background: linear-gradient(135deg, #9E9E9E, #616161);
}

.bg-desarmes {
    background: linear-gradient(135deg, #7C4DFF, #512DA8);
}

.bg-faltas {
    background: linear-gradient(135deg, #FF9100, #E65100);
}

.bg-indiretas {
    background: linear-gradient(135deg, #FF5252, #B71C1C);
}
</style>
""", unsafe_allow_html=True)


def gerar_pdf_jogo(jogo, score_formatado, analise_texto, img_barra, img_radar):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        caminho_pdf = tmp.name

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    story = []

    # 🔹 TÍTULO
    story.append(Paragraph("<b>Relatório de Desempenho do Jogo</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    # 🔹 DADOS DO JOGO
    dados_jogo = f"""
    <b>Data:</b> {jogo['Data']}<br/>
    <b>Jogo:</b> {jogo['Casa']} x {jogo['Visitante']}<br/>
    <b>Modalidade:</b> {jogo.get('Condição do Campo', '-')}<br/>
    <b>Minutagem:</b> {jogo.get('Minutos', 0)} min
    """
    story.append(Paragraph(dados_jogo, styles["Normal"]))
    story.append(Spacer(1, 14))

    # 🔹 SCORE
    story.append(Paragraph(f"<b>Score Geral do Jogo:</b> {score_formatado}", styles["Heading2"]))
    story.append(Spacer(1, 14))

    # 🔹 SCOUTS
    tabela_dados = [
        ["Scout", "Valor"],
        ["Chutes Certos", jogo["Chutes"]],
        ["Chutes Errados", jogo.get("Chutes Errados", 0)],
        ["Passes-chave", jogo["Passes-chave"]],
        ["Passes Errados", jogo.get("Passes Errados", 0)],
        ["Desarmes", jogo["Desarmes"]],
        ["Faltas Sofridas", jogo["Faltas Sofridas"]],
        ["Participações", jogo["Participações Indiretas"]],
    ]

    tabela = Table(tabela_dados, colWidths=[9 * cm, 3 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0E1117")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, white),
        ("ALIGN", (1, 1), (-1, -1), "CENTER")
    ]))

    story.append(tabela)
    story.append(Spacer(1, 16))

    # 🔹 GRÁFICOS
    story.append(Paragraph("<b>Distribuição de Scouts</b>", styles["Heading2"]))
    story.append(Image(img_barra, width=16 * cm, height=7 * cm))
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>Radar de Desempenho</b>", styles["Heading2"]))
    story.append(Image(img_radar, width=14 * cm, height=14 * cm))
    story.append(Spacer(1, 18))

    # 🔹 ANÁLISE TÉCNICA
    story.append(Paragraph("<b>Análise Técnica do Jogo</b>", styles["Heading2"]))
    story.append(Paragraph(analise_texto.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)

    return caminho_pdf

def gerar_barra_pdf(jogo, scout_cols):
    fig, ax = plt.subplots(figsize=(8, 4))

    valores = jogo[scout_cols].values
    cores = [SCOUT_COLORS[s] for s in scout_cols]

    ax.bar(scout_cols, valores, color=cores)

    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")

    ax.tick_params(colors="white", rotation=45)
    ax.set_title("Distribuição de Scouts", color="white")
    ax.grid(axis="y", linestyle=":", alpha=0.3)

    for i, val in enumerate(valores):
        ax.text(i, val + 0.1, str(int(val)), ha="center", color="white", fontsize=9)

    caminho = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plt.tight_layout()
    plt.savefig(caminho, dpi=200)
    plt.close(fig)

    return caminho

def gerar_radar_pdf(jogo, scout_cols, df):
    radar_vals = []
    for scout in scout_cols:
        max_val = df_jogos_full[scout].max()
        valor = jogo[scout]
        radar_vals.append((valor / max_val) * 100 if max_val > 0 else 0)

    radar_vals += radar_vals[:1]
    labels = scout_cols + [scout_cols[0]]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(6, 6))

    ax.plot(labels, radar_vals, color="#00E5FF", linewidth=2)
    ax.fill(labels, radar_vals, color="#00E5FF", alpha=0.35)

    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")

    ax.tick_params(colors="white")
    ax.set_title("Radar de Scouts (estilo FIFA)", color="white", pad=20)

    caminho = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plt.tight_layout()
    plt.savefig(caminho, dpi=200)
    plt.close(fig)

    return caminho


if st.session_state["pagina"] == "dashboard":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.markdown("## 📊 Dashboard de Performance do Atleta")
    st.markdown("---")

    # --- 2. CARREGAR DADOS COMPLETOS ---
    df_jogos_full = load_registros()
    df_treinos_full = load_treinos_df()
    df_sono_full = load_sono_df()

    # ATENÇÃO: Tratamento para evitar ArrowTypeError devido a formatos de data mistos.
    if 'Data' in df_jogos_full.columns:
        df_jogos_full['Data'] = df_jogos_full['Data'].astype(str)
    if 'Date' in df_treinos_full.columns:
        df_treinos_full['Date'] = df_treinos_full['Date'].astype(str)
    if 'Data' in df_sono_full.columns:
        df_sono_full['Data_DT'] = pd.to_datetime(
            df_sono_full['Data'],
            dayfirst=True,
            errors="coerce"
        )

    # --- NOVO BLOCO DE NORMALIZAÇÃO (Aplicar antes dos filtros de data) ---
    NOME_COLUNA_TIME = 'Treino'  # Definindo aqui para uso em todo o bloco
    NOME_COLUNA_TIPO = 'Tipo'

    if NOME_COLUNA_TIME in df_treinos_full.columns:
        # NORMALIZAÇÃO PARA TREINOS: Remove espaços, padroniza capitalização
        df_treinos_full[NOME_COLUNA_TIME] = df_treinos_full[NOME_COLUNA_TIME].astype(str).str.strip().str.title()

    if NOME_COLUNA_TIPO in df_treinos_full.columns:
        # NORMALIZAÇÃO PARA TIPOS: Remove espaços, padroniza capitalização
        df_treinos_full[NOME_COLUNA_TIPO] = df_treinos_full[NOME_COLUNA_TIPO].astype(str).str.strip().str.title()

    if 'Casa' in df_jogos_full.columns:
        # NORMALIZAÇÃO PARA TIMES/JOGOS (Para garantir consistência nos filtros)
        df_jogos_full['Casa'] = df_jogos_full['Casa'].astype(str).str.strip().str.title()

    # --- 1. FILTRO DE PERÍODO E NOVOS FILTROS ---

    # Definindo datas padrão para o filtro (últimos 30 dias)
    hoje = pd.to_datetime('today').date()
    trinta_dias_atras = hoje - pd.Timedelta(days=30)

    # 1.1. Filtros de Data
    col_date1, col_date2, col_date3 = st.columns([1, 1, 3])

    with col_date1:
        data_inicio = st.date_input("🗓️ Data Inicial", trinta_dias_atras)
    with col_date2:
        data_fim = st.date_input("🗓️ Data Final", hoje)
    with col_date3:
        # Título de contexto
        st.markdown(
            f'<div style="text-align: right; padding-top: 15px;">**Visão Geral** (De {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")})</div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🔍 Filtros Adicionais de Jogos")

    # 1.2. Prepara as opções para os novos filtros
    times_atleta_options = sorted([t for t in df_jogos_full['Casa'].astype(str).unique() if t and t.strip() != "nan"])
    campeonatos_options = sorted(
        [c for c in df_jogos_full['Campeonato'].astype(str).unique() if c and c.strip() != "nan"])
    modalidades_options = sorted(
        [m for m in df_jogos_full['Condição do Campo'].astype(str).unique() if m and m.strip() != "nan"])

    # 1.3. Widgets dos Novos Filtros (3 Colunas)
    col_filter_t, col_filter_c, col_filter_m = st.columns(3)

    with col_filter_t:
        time_filter = st.selectbox("Time do Atleta:", ["Todos"] + times_atleta_options, key="dash_time")
    with col_filter_c:
        campeonato_filter = st.selectbox("Campeonato:", ["Todos"] + campeonatos_options, key="dash_camp")
    with col_filter_m:
        modalidade_filter = st.selectbox("Modalidade:", ["Todos"] + modalidades_options, key="dash_modal")

    st.markdown("---")

    # --- 2. APLICAR FILTRO DE DATA EM TODOS OS DATAFRAMES ---

    df_jogos_f = filter_df_by_date(df_jogos_full, 'Data', data_inicio, data_fim)
    df_treinos_f = filter_df_by_date(df_treinos_full, 'Date', data_inicio, data_fim)
    df_sono_f = filter_df_by_date(df_sono_full, 'Data', data_inicio, data_fim)

    # --- PREPARAR DADOS DE SONO PARA USO IMEDIATO ---
    if not df_sono_f.empty and 'Duração do Sono (h:min)' in df_sono_f.columns:
        df_sono_f['Duração_Horas'] = df_sono_f['Duração do Sono (h:min)'].apply(parse_duration_to_hours)

    # --- 3. APLICAR NOVOS FILTROS NO DATAFRAME DE JOGOS (df_jogos_f) ---

    # Variável para armazenar o time filtrado (se for "Todos" será None)
    time_filtrado_selecionado = None

    if time_filter != "Todos":
        df_jogos_f = df_jogos_f[df_jogos_f['Casa'].astype(str) == time_filter]
        time_filtrado_selecionado = time_filter  # Armazena o nome do time para o card de Treinos

    if campeonato_filter != "Todos":
        df_jogos_f = df_jogos_f[df_jogos_f['Campeonato'].astype(str) == campeonato_filter]

    if modalidade_filter != "Todos":
        df_jogos_f = df_jogos_f[df_jogos_f['Condição do Campo'].astype(str) == modalidade_filter]

    # --- FIM DOS FILTROS ---

    # Cálculo das métricas básicas (agora retorna media_sono_decimal)
    (total_jogos, total_gols, total_assistencias,
     total_minutos, total_treinos, media_sono_formatada, media_sono_decimal) = calculate_metrics(
        df_jogos_f, df_treinos_f, df_sono_f
    )

    # CALCULA O TOTAL DE DIAS NO PERÍODO PARA O ENGAJAMENTO
    total_dias_periodo = (pd.to_datetime(data_fim) - pd.to_datetime(data_inicio)).days + 1

    # --- CÁLCULO PARA TREINOS BASEADO NO FILTRO DE TIME (Requisito) ---
    total_treinos_display = total_treinos
    treino_label = "Sessões Concluídas"

    # Nome da coluna que contem o time, exatamente como está na planilha
    NOME_COLUNA_TIME = 'Treino'

    # DataFrame para aplicar filtros adicionais (Time e Modalidade)
    df_treinos_calculo = df_treinos_f.copy()

    # Define se os filtros de Time ou Modalidade estão ativos (assumindo que modalidade_filter existe no escopo)
    is_time_filter_active = (time_filtrado_selecionado and time_filtrado_selecionado != "Todos")
    is_modalidade_filter_active = ('modalidade_filter' in locals() and modalidade_filter != "Todos")

    # 1. FILTRO POR TIME
    if is_time_filter_active and NOME_COLUNA_TIME in df_treinos_calculo.columns:
        termo_pesquisa = time_filtrado_selecionado.strip().lower()
        df_treinos_calculo = df_treinos_calculo[
            df_treinos_calculo[NOME_COLUNA_TIME].astype(str).str.lower().str.contains(termo_pesquisa, na=False)
        ]

    # 2. FILTRO POR MODALIDADE
    # Usamos a coluna 'Tipo' para filtrar por modalidade.
    if is_modalidade_filter_active and 'Tipo' in df_treinos_calculo.columns:
        modalidade_lower = modalidade_filter.strip().lower()
        df_treinos_calculo = df_treinos_calculo[
            df_treinos_calculo['Tipo'].astype(str).str.lower().str.contains(modalidade_lower, na=False)
        ]

    # 3. ATUALIZAÇÃO DO CARD (Se Time OU Modalidade estiver ativo)
    if is_time_filter_active or is_modalidade_filter_active:

        total_filtrado = df_treinos_calculo.shape[0]
        total_treinos_display = total_filtrado  # FORÇA a exibição do valor filtrado

        if total_filtrado > 0:
            # Define um rótulo mais informativo baseado nos filtros ativos
            if is_modalidade_filter_active and not is_time_filter_active:
                treino_label = f"Treinos de '{modalidade_filter}'"
            elif is_time_filter_active and not is_modalidade_filter_active:
                treino_label = f"Treinos de '{time_filtrado_selecionado}'"
            else:  # Ambos ativos ou outros cenários (Apenas o filtro de Time já garante isso)
                treino_label = "Sessões Filtradas"
        else:
            treino_label = "Nenhum treino encontrado"

    # Se 'Treino' estava ausente e o filtro de time estava ativo (caso de erro original)
    elif time_filtrado_selecionado and NOME_COLUNA_TIME not in df_treinos_f.columns:
        total_treinos_display = total_treinos
        treino_label = f"Treino: Coluna '{NOME_COLUNA_TIME}' Ausente"

    # --------------------------------------------------------------------------
    # 3. CARDS DE INDICADORES (TOPO)
    # --------------------------------------------------------------------------

    # --- 3.1. CÁLCULOS ADICIONAIS: AVALIAÇÃO TÉCNICA E ENGAJAMENTO ---

    # ** CÁLCULO DA AVALIAÇÃO TÉCNICA **
    # ATENÇÃO: A função AGORA retorna a nota E a conclusão
    avaliacao_tecnica, conclusao_avaliacao = calculate_avaliacao_tecnica(
        df_jogos_f, modalidade_filter, time_filter  # Passando os filtros
    )

    # ** CÁLCULO DO ENGAJAMENTO **
    engajamento = calculate_engajamento(
        df_treinos_f, df_sono_f, total_dias_periodo, media_sono_decimal
    )


    def calcular_vitoria(resultado_str):
        if pd.isna(resultado_str): return 0
        try:
            partes = str(resultado_str).strip().split('x')
            if len(partes) == 2:
                gols_atleta = int(partes[0].strip())
                gols_adversario = int(partes[1].strip())
                return 1 if gols_atleta > gols_adversario else 0
        except ValueError:
            return 0
        return 0


    # Chamada para a função que também retorna os totais de V, E, D
    def analisar_resultado(df):
        if 'Resultado' not in df.columns or df.empty:
            return 0, 0, 0, 0

        df_temp = df.copy()
        df_temp['Vitoria'] = df_temp['Resultado'].apply(lambda x: 1 if calcular_vitoria(x) == 1 else 0)
        df_temp['Empate'] = df_temp['Resultado'].apply(
            lambda x: 1 if str(x).strip().lower().replace(' ', '') in ['0x0', '1x1', '2x2', '3x3', '4x4', '5x5', '6x6',
                                                                       '7x7', '8x8', '9x9'] else 0)

        # Derrota = Não é vitória e não é empate
        def calcular_derrota(row):
            if row['Vitoria'] == 1 or row['Empate'] == 1:
                return 0

            # Recalcula a derrota com base no resultado (se a vitória for 0 e o empate 0)
            try:
                partes = str(row['Resultado']).strip().split('x')
                if len(partes) == 2:
                    gols_atleta = int(partes[0].strip())
                    gols_adversario = int(partes[1].strip())
                    return 1 if gols_atleta < gols_adversario else 0
            except ValueError:
                return 0
            return 0

        df_temp['Derrota'] = df_temp.apply(calcular_derrota, axis=1)

        total_jogos_vd = df_temp.shape[0]
        vitorias_vd = df_temp['Vitoria'].sum()
        empates_vd = df_temp['Empate'].sum()
        derrotas_vd = df_temp['Derrota'].sum()

        return total_jogos_vd, vitorias_vd, empates_vd, derrotas_vd


    # Chamada para obter os totais de V, E, D
    total_jogos_vd, vitorias_vd, empates_vd, derrotas_vd = analisar_resultado(df_jogos_f)

    # CÁLCULO DA PORCENTAGEM DE VITÓRIAS
    vitorias = vitorias_vd
    if total_jogos > 0:
        vitorias_percent = f"{(vitorias / total_jogos * 100):.0f}%"
    else:
        vitorias_percent = "0%"

    # CÁLCULO DA PORCENTAGEM DE DERROTAS (NOVO REQUISITO)
    derrotas_percent = "0%"
    if total_jogos > 0:
        derrotas_percent_val = (derrotas_vd / total_jogos * 100)
        derrotas_percent = f"{derrotas_percent_val:.0f}%"

    # CÁLCULO DA MÉDIA DE GOLS
    media_gols = total_gols / total_jogos if total_jogos > 0 else 0.0
    media_gols_formatada = f"{media_gols:.2f}"

    # LOGICA DA MODALIDADE
    if modalidade_filter != "Todos":
        modalidade_exibida = modalidade_filter
        modalidade_subtexto = "Modalidade Filtrada"
    elif not df_jogos_f.empty and 'Condição do Campo' in df_jogos_f.columns:
        modalidade_exibida = "Todas"
        modalidade_subtexto = "Tipos de Jogo (Filtro Todos)"
    else:
        modalidade_exibida = "N/A"
        modalidade_subtexto = "Tipo de Jogo"

    # ======================================================
    # 🧠 INSIGHT AUTOMÁTICO DE IMPACTO OFENSIVO
    # ======================================================

    insight_texto = None

    if not df_jogos_f.empty:
        df_insight = df_jogos_f.copy()

        # Garante valores numéricos
        df_insight["Gols Marcados"] = pd.to_numeric(df_insight["Gols Marcados"], errors="coerce").fillna(0)
        df_insight["Assistências"] = pd.to_numeric(df_insight["Assistências"], errors="coerce").fillna(0)

        # Jogos com gol + assistência
        jogos_impacto = df_insight[
            (df_insight["Gols Marcados"] > 0) |
            (df_insight["Assistências"] > 0)
            ]

        if not jogos_impacto.empty:
            total_impacto = len(jogos_impacto)

            # Calcula vitórias nesses jogos
            vitorias_impacto = jogos_impacto["Resultado"].apply(calcular_vitoria).sum()

            perc_vitoria = int((vitorias_impacto / total_impacto) * 100)

            insight_texto = (
                f"📌 Em **{total_impacto} jogos** com participação ofensiva do atleta "
                f"(gol ou assistência), "
                f"o time venceu **{vitorias_impacto}**, "
                f"resultando em **{perc_vitoria}%** de aproveitamento nesses jogos."
            )

    # --- 3.2. PRIMEIRA LINHA DE CARDS (6 COLUNAS) ---
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Coluna 1: Total de Jogos (AZUL CLARO - Cor Jogos)
    with col1:
        st.markdown(f'''
                    <div class="card-jogos">
                        🏟️ JOGOS<p>{total_jogos}</p>
                        <label>Minutos Jogados Total</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 2: Gols Total
    with col2:
        st.markdown(f'''
                    <div class="card-gols">
                        ⚽ GOLS<p>{total_gols}</p>
                        <label>Total Marcados</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 3: Assistências Total
    with col3:
        st.markdown(f'''
                    <div class="card-assistencias">
                        🎯 ASSISTÊNCIAS<p>{total_assistencias}</p>
                        <label>Total</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 4: Minutos Total
    with col4:
        st.markdown(f'''
                    <div class="card-minutos">
                        ⏱️ MINUTAGEM<p>{total_minutos}</p>
                        <label>Total em Campo</label>
                    </div>''', unsafe_allow_html=True)

    # Coluna 5: Total de Treinos
    with col5:
        st.markdown(f'''
                    <div class="card-treinos">
                        💪 TREINOS<p>{total_treinos_display}</p>
                        <label>{treino_label}</label>
                    </div>''', unsafe_allow_html=True)

    # Coluna 6: Média de Sono
    with col6:
        st.markdown(f'''
                    <div class="card-sono">
                        💤 MÉDIA SONO<p>{media_sono_formatada}</p>
                        <label>Média Diária</label>
                    </div>''', unsafe_allow_html=True)

    # --- 3.3. SEGUNDA LINHA DE CARDS ---
    col7, col8, col9, col10, col11, col12 = st.columns(6)

    # Coluna 7: MODALIDADE (Requisito)
    with col7:
        st.markdown(f'''
                    <div class="card-jogos">
                        🥅 MODALIDADE<p>{modalidade_exibida}</p>
                        <label>{modalidade_subtexto}</label>
                    </div>''', unsafe_allow_html=True)

    # Coluna 8: MÉDIA DE GOLS (Requisito)
    with col8:
        st.markdown(f'''
                    <div class="card-gols">
                        ⚽ MÉDIA GOLS<p>{media_gols_formatada}</p>
                        <label>Gols por Jogo</label>
                    </div>''', unsafe_allow_html=True)

    # Coluna 9: PORCENTAGEM DE DERROTAS (NOVO CARD - Vermelho para Alerta)
    with col9:
        # Estilo inline para cor vermelha no valor
        st.markdown(f'''
                    <div class="card-derrotas">
                        ❌ DERROTAS (%)<p style="color: #FF6347;">{derrotas_percent}</p>
                        <label>No Período Selecionado</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 10: Vitórias %
    with col10:
        st.markdown(f'''
                    <div class="card-sono">
                        🏆 VITÓRIAS(%)<p>{vitorias_percent}</p>
                        <label>No Período Selecionado</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 11: Avaliação Técnica (CALCULADO)
    with col11:
        st.markdown(f'''
                    <div class="card-treinos">
                        ⭐ AVALIAÇÃO TÉCNICA<p>{avaliacao_tecnica}</p>
                        <label>Ficha Ajustada</label>
                    </div>''', unsafe_allow_html=True)
    # Coluna 12: Engajamento (CALCULADO)
    with col12:
        st.markdown(f'''
                    <div class="card-minutos">
                        🧠 ENGAJAMENTO<p>{engajamento}</p>
                        <label>Sono e Disciplina</label>
                    </div>''', unsafe_allow_html=True)

    if insight_texto:
        st.success(insight_texto)

    # --- 3.4. CONCLUSÃO DA AVALIAÇÃO TÉCNICA ---
    # Adicione este bloco para exibir o texto explicativo
    if conclusao_avaliacao and conclusao_avaliacao != "Não há dados de jogos para o período/filtros selecionados.":
        st.markdown("##### 📝 Conclusão da Avaliação Técnica")
        # Usando st.info ou st.markdown com estilo para destaque
        st.info(conclusao_avaliacao)

    st.markdown("---")

    # --- 4. GRÁFICOS (ABAIXO DOS CARDS) ---
    col_g1, col_g2 = st.columns([2, 1])

    # GRÁFICO 1: Gols por Campeonato / Adversário
    with col_g1:
        st.markdown("### 📊 Gols por Campeonato / Adversário")

        if df_jogos_f.empty:
            st.info("Não há registros de jogos no período/filtros selecionados para o gráfico.")
        else:
            # --- CÁLCULO E FORMATAÇÃO DE V/E/D ---
            # Já temos total_jogos_vd, vitorias_vd, empates_vd, derrotas_vd calculados acima
            if total_jogos_vd > 0:
                resumo_ved = f"({total_jogos_vd} J, {vitorias_vd} V, {empates_vd} E, {derrotas_vd} D)"
            else:
                resumo_ved = ""
            # ---------------------------------------------

            # Preparação dos dados
            df_jogos_f_g = df_jogos_f.copy()
            df_jogos_f_g['Gols Marcados'] = pd.to_numeric(df_jogos_f_g['Gols Marcados'], errors='coerce').fillna(0)
            df_jogos_f_g = df_jogos_f_g.sort_values(by='Data_DT', ascending=True)
            group_gols = df_jogos_f_g.groupby(["Data_DT", "Visitante", "Campeonato"], dropna=False)[
                "Gols Marcados"].sum().reset_index()

            group_gols['Rotulo'] = group_gols['Visitante'] + ' (' + group_gols['Data_DT'].dt.strftime('%d/%m') + ')'

            # --- Plotagem (Matplotlib Dark Mode) ---

            fig_gols, ax_gols = plt.subplots(figsize=(12, 6))

            # Cores dinâmicas para Campeonatos
            from matplotlib.patches import Patch

            unique_camps = group_gols['Campeonato'].unique()
            cores_campeonato = {camp: plt.cm.get_cmap('Dark2')(i % 8) for i, camp in enumerate(unique_camps)}
            cores_barras = [cores_campeonato.get(c, 'gray') for c in group_gols["Campeonato"]]

            x = range(len(group_gols))
            ax_gols.bar(x, group_gols["Gols Marcados"].values, color=cores_barras, edgecolor='white', linewidth=0.5)

            # Estilo Dark Mode para o Matplotlib
            fig_gols.patch.set_facecolor('#0E1117')
            ax_gols.set_facecolor('#0E1117')
            plt.rcParams['text.color'] = 'white'
            ax_gols.tick_params(axis='x', colors='white')
            ax_gols.tick_params(axis='y', colors='white')
            ax_gols.spines['bottom'].set_color('white')
            ax_gols.spines['left'].set_color('white')
            ax_gols.yaxis.label.set_color('white')
            ax_gols.xaxis.label.set_color('white')

            # Adiciona os filtros ativos ao título do gráfico
            filtro_titulo = ""
            if time_filter != "Todos": filtro_titulo += f" | Time: {time_filter}"
            if campeonato_filter != "Todos": filtro_titulo += f" | Camp.: {campeonato_filter}"
            if modalidade_filter != "Todos": filtro_titulo += f" | Modal.: {modalidade_filter}"

            # ADICIONANDO O RESUMO V/E/D AO TÍTULO
            titulo_final = f"Gols Marcados por Jogo/Campeonato{filtro_titulo} {resumo_ved}"
            ax_gols.set_title(titulo_final, color='white', fontsize=14)

            ax_gols.set_xticks(x)
            ax_gols.set_xticklabels(group_gols["Rotulo"].values, rotation=60, ha='right', fontsize=8)
            ax_gols.set_ylabel("Gols Marcados")

            # Legenda
            legend_handles = [Patch(facecolor=cores_campeonato[c], label=c) for c in unique_camps]
            ax_gols.legend(handles=legend_handles, title="Campeonatos", loc='upper left', bbox_to_anchor=(1.05, 1),
                           facecolor='#1F2430', edgecolor='white', labelcolor='white')

            plt.tight_layout()
            st.pyplot(fig_gols)
            plt.close(fig_gols)

    # GRÁFICO 2: Treinos por Tipo (Inalterado)
    with col_g2:
        st.markdown("### 📈 Treinos por Tipo")

        # --- CÓDIGO DE FILTRAGEM ---
        df_treinos_grafico = df_treinos_f.copy()  # Já filtrado por data ajustada

        # 1. FILTRO POR TIME
        # Esta filtragem só ocorrerá se um Time ESPECÍFICO for selecionado.
        if time_filtrado_selecionado and 'Treino' in df_treinos_f.columns:
            termo_pesquisa = time_filtrado_selecionado.strip().lower()
            df_treinos_grafico = df_treinos_grafico[
                df_treinos_grafico['Treino'].astype(str).str.lower().str.contains(termo_pesquisa, na=False)
            ]

        # 2. FILTRO POR MODALIDADE
        if 'modalidade_filter' in locals() and modalidade_filter != "Todos" and 'Tipo' in df_treinos_f.columns:
            modalidade_lower = modalidade_filter.strip().lower()
            df_treinos_grafico = df_treinos_grafico[
                df_treinos_grafico['Tipo'].astype(str).str.lower().str.contains(modalidade_lower, na=False)
            ]
        # -------------------------------------------------------------------------

        if df_treinos_grafico.empty:
            st.info("Não há registros de treinos no período ou para os filtros selecionados.")
        else:
            # *** LÓGICA DE AGRUPAMENTO DINÂMICO ***

            # Se NENHUM time específico foi filtrado E a modalidade foi filtrada, agrupamos por TIME.
            if time_filter == "Todos" and modalidade_filter != "Todos" and NOME_COLUNA_TIME in df_treinos_grafico.columns:
                # Agrupar por Time (coluna 'Treino')
                coluna_agrupamento = NOME_COLUNA_TIME
                titulo_agrupamento = f"Treinos por Time (Modalidade: {modalidade_filter})"
            else:
                # Agrupar por Tipo de Treino (Padrão)
                coluna_agrupamento = 'Tipo'
                titulo_agrupamento = "Distribuição de Tipos de Treino"

            # Se a coluna de agrupamento não existir, volta para o padrão "Tipo" (segurança)
            if coluna_agrupamento not in df_treinos_grafico.columns:
                coluna_agrupamento = 'Tipo'
                titulo_agrupamento = "Distribuição de Tipos de Treino (Padrão)"

            # Lógica de Agrupamento
            contagem_grupo = df_treinos_grafico[coluna_agrupamento].value_counts()
            df_plot = contagem_grupo.reset_index()
            df_plot.columns = [coluna_agrupamento, 'Contagem']
            total_treinos_grafico = len(df_treinos_grafico)

            # --- GRÁFICO DE BARRAS HORIZONTAIS (Matplotlib Dark Mode) ---
            fig_treinos, ax_treinos = plt.subplots(figsize=(6, 6))

            # Estilo Dark Mode para o Matplotlib
            fig_treinos.patch.set_facecolor('#0E1117')
            ax_treinos.set_facecolor('#0E1117')
            ax_treinos.tick_params(axis='x', colors='white')
            ax_treinos.tick_params(axis='y', colors='white')
            ax_treinos.spines['bottom'].set_color('white')
            ax_treinos.spines['left'].set_color('white')
            ax_treinos.yaxis.label.set_color('white')
            ax_treinos.xaxis.label.set_color('white')

            # Cores e Plotagem
            df_plot = df_plot.sort_values(by='Contagem', ascending=False)
            cores = ['#9C27B0'] * len(df_plot)

            # Gráfico de Barras Horizontais
            ax_treinos.barh(df_plot[coluna_agrupamento], df_plot['Contagem'], color=cores, height=0.7)

            # Adiciona o rótulo da contagem em cada barra
            for index, value in enumerate(df_plot['Contagem']):
                ax_treinos.text(value, index, f" {value}", color='white', va='center')

            # Atualiza o título para refletir a contagem correta após o filtro
            ax_treinos.set_title(f"{titulo_agrupamento} ({total_treinos_grafico} no total)", color='white')
            ax_treinos.set_xlabel("Número de Sessões")
            ax_treinos.grid(axis='x', linestyle=':', alpha=0.3)

            ax_treinos.set_xlim(right=df_plot['Contagem'].max() * 1.2)

            plt.tight_layout()
            st.pyplot(fig_treinos)
            plt.close(fig_treinos)

    st.markdown("---")

    # ===============================================
    # 🎨 Paleta FIFA
    SCOUT_COLORS = {
        "Chutes": "#00E5FF",  # Ciano
        "Chutes Errados": "#FF1744",  # vermelho forte
        "Desarmes": "#7C4DFF",  # Roxo
        "Passes-chave": "#00E676",  # Verde
        "Passes Errados": "#9E9E9E",  # CINZA
        "Faltas Sofridas": "#FF9100",  # Laranja
        "Participações Indiretas": "#FF5252"  # Vermelho

    }


    def hex_to_rgba(hex_color, alpha=0.35):
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"


    # 📊 ANÁLISE DE SCOUTS
    # ======================================================

    st.markdown("## 📊 Análise de Scouts")

    # Garante colunas
    scout_cols = [
        "Chutes",
        "Chutes Errados",
        "Desarmes",
        "Passes-chave",
        "Passes Errados",
        "Faltas Sofridas",
        "Participações Indiretas"
    ]

    for c in scout_cols:
        if c not in df_jogos_full.columns:
            df_jogos_full[c] = 0
        df_jogos_full[c] = pd.to_numeric(
            df_jogos_full[c], errors="coerce"
        ).fillna(0)

    # ---------------------------
    # MODO DE VISUALIZAÇÃO
    # ---------------------------
    modo_scout = st.radio(
        "Modo de análise:",
        [
            "🎯 Scout por jogo",
            "📊 Média por jogo",
            "⚖️ Comparação por modalidade"
        ],
        horizontal=True
    )

    # ======================================================
    # 🎯 1️⃣ SCOUT POR JOGO
    # ======================================================
    if modo_scout == "🎯 Scout por jogo":

        df_jogos = df_jogos_full.copy()


        df_jogos["Data_DT"] = pd.to_datetime(
            df_jogos["Data"], dayfirst=True, errors="coerce"
        )
        df_jogos = df_jogos.sort_values("Data_DT", ascending=False)

        df_jogos["Jogo"] = (
                df_jogos["Data"].astype(str) + " | " +
                df_jogos["Casa"] + " x " +
                df_jogos["Visitante"]
        )

        jogo_sel = st.selectbox(
            "Selecione o jogo:",
            df_jogos["Jogo"].unique(),
            key="select_jogo_scout"
        )

        jogo = df_jogos[df_jogos["Jogo"] == jogo_sel].iloc[0]

        # ---------------- MÉTRICAS ----------------
        col1, col2, col3, col4 = st.columns(4)
        col5, col6, col7 = st.columns(3)

        with col1:
            st.markdown(f"""
                    <div class="scout-card bg-chutes">
                        <div class="icon">🥅</div>
                        <div class="scout-title">Chutes Certos</div>
                        <div class="scout-value">{int(jogo["Chutes"])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                    <div class="scout-card bg-chutes-errados">
                        <div class="icon">❌</div>
                        <div class="scout-title">Chutes Errados</div>
                        <div class="scout-value">{int(jogo.get("Chutes Errados", 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                    <div class="scout-card bg-passes">
                        <div class="icon">🎯</div>
                        <div class="scout-title">Passes-chave</div>
                        <div class="scout-value">{int(jogo["Passes-chave"])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
                    <div class="scout-card bg-passes-errados">
                        <div class="icon">📉</div>
                        <div class="scout-title">Passes Errados</div>
                        <div class="scout-value">{int(jogo.get("Passes Errados", 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
                    <div class="scout-card bg-desarmes">
                        <div class="icon">🛡️</div>
                        <div class="scout-title">Desarmes</div>
                        <div class="scout-value">{int(jogo["Desarmes"])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
                    <div class="scout-card bg-faltas">
                        <div class="icon">⚡</div>
                        <div class="scout-title">Faltas Sofridas</div>
                        <div class="scout-value">{int(jogo["Faltas Sofridas"])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col7:
            st.markdown(f"""
                    <div class="scout-card bg-indiretas">
                        <div class="icon">🔁</div>
                        <div class="scout-title">Participações</div>
                        <div class="scout-value">{int(jogo["Participações Indiretas"])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # ---------------- GRÁFICO ----------------
        scout_vals = jogo[scout_cols]

        fig_barra = px.bar(
            x=scout_vals.index,
            y=scout_vals.values,
            color=scout_vals.index,
            color_discrete_map=SCOUT_COLORS,
            text=scout_vals.values,  # 👈 MOSTRA OS VALORES
            labels={"x": "Scout", "y": "Quantidade"},
            title="Distribuição de Scouts no Jogo"
        )

        fig_barra.update_traces(
            texttemplate='%{y}',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(
                color='white',
                size=14
            )
        )

        fig_barra.update_layout(
            showlegend=False,
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            dragmode=False,
            hovermode=False
        )

        fig_barra.update_xaxes(fixedrange=True)
        fig_barra.update_yaxes(fixedrange=True)

        st.plotly_chart(
            fig_barra,
            use_container_width=True,
            config={
                "scrollZoom": False,
                "displayModeBar": False,
                "doubleClick": False,
                "staticPlot": True
            }
        )

        # ---------------- RADAR ----------------
        st.markdown("### 🎮 Radar de Scouts")

        radar_vals = []
        for scout in scout_cols:
            max_val = df_jogos_full[scout].max()
            valor = jogo[scout]
            radar_vals.append((valor / max_val) * 100 if max_val > 0 else 0)

        radar_vals += radar_vals[:1]
        radar_labels = scout_cols + [scout_cols[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=radar_vals,
                theta=radar_labels,
                mode="lines",
                fill="toself",
                line=dict(color="#00E5FF", width=4),
                fillcolor="rgba(0,229,255,0.35)"
            )
        )

        fig_radar.update_layout(
            polar=dict(
                bgcolor="#0E1117",
                radialaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.15)"),
                angularaxis=dict(tickfont=dict(color="white"))
            ),
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            showlegend=False,
            height=500
        )

        st.plotly_chart(
            fig_radar,
            use_container_width=True,
            config={
                "scrollZoom": False,
                "displayModeBar": False,
                "doubleClick": False,
                "staticPlot": True
            }
        )

        # ======================================================
        # ======================================================
        # ⭐ SCORE GERAL DO JOGO (LÓGICA COMPLETA E REAL)
        # ======================================================

        st.markdown("### ⭐ Score Geral do Jogo")

        # 📌 Dados do jogo
        gols = int(jogo.get("Gols Marcados", 0))
        assistencias = int(jogo.get("Assistências", 0))
        passes_chave = int(jogo.get("Passes-chave", 0))
        desarmes = int(jogo.get("Desarmes", 0))
        faltas = int(jogo.get("Faltas Sofridas", 0))
        participacoes = int(jogo.get("Participações Indiretas", 0))

        chutes_certos = int(jogo.get("Chutes", 0))
        chutes_errados = int(jogo.get("Chutes Errados", 0))
        finalizacoes = chutes_certos + chutes_errados

        passes_errados = int(jogo.get("Passes Errados", 0))
        erros_total = chutes_errados + passes_errados

        # ===============================
        # 🔢 COMPONENTES DO SCORE
        # ===============================

        # ⚽ ATAQUE (peso alto)
        score_gols = gols * 2.2
        score_assistencia = assistencias * 1.8

        # 🎯 CRIAÇÃO DE JOGO
        score_passes_chave = passes_chave * 0.6
        score_participacoes = participacoes * 0.4
        score_faltas = faltas * 0.3

        # 🛡️ DEFESA
        score_defesa = desarmes * 0.5

        # ⚡ EFICIÊNCIA NAS FINALIZAÇÕES
        score_eficiencia = 0
        if finalizacoes > 0:
            eficiencia = gols / finalizacoes
            score_eficiencia = eficiencia * 1.5

        # ❌ ERROS (penalidade CONTROLADA)
        penalidade_erros = erros_total * 0.35

        # ===============================
        # ⭐ SCORE FINAL
        # ===============================
        score_final = (
                score_gols +
                score_assistencia +
                score_passes_chave +
                score_participacoes +
                score_faltas +
                score_defesa +
                score_eficiencia -
                penalidade_erros
        )

        # ===============================
        # ⚖️ AJUSTE POR MODALIDADE
        # ===============================
        modalidade = jogo["Condição do Campo"]

        fator = {
            "Futsal": 1.0,
            "Society": 0.9,
            "Campo": 0.8
        }.get(modalidade, 1.0)

        score_final = score_final / fator

        # Normaliza 0–10
        score_final = max(0, min(10, score_final))
        score_formatado = f"{score_final:.1f}"

        # 🎨 Cor dinâmica
        if score_final >= 7.5:
            cor_score = "#00E676"  # Verde
        elif score_final >= 5.8:
            cor_score = "#FFB300"  # Amarelo
        else:
            cor_score = "#FF1744"  # Vermelho

        # 🧱 Card visual (SEM ALTERAR ESTILO)
        st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {cor_score}, #0E1117);
                    border-radius: 20px;
                    padding: 25px;
                    text-align: center;
                    color: white;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
                ">
                    <div style="font-size:18px; opacity:0.9;">Desempenho Geral</div>
                    <div style="font-size:54px; font-weight:bold;">{score_formatado}</div>
                    <div style="opacity:0.85;">Nota baseada em impacto ofensivo, criação, defesa e erros</div>
                </div>
                """, unsafe_allow_html=True)

        # ======================================================
        # 📝 ANÁLISE TÉCNICA DO JOGO (AGORA NO LUGAR CERTO)
        # ======================================================
        st.markdown("### 📝 Análise Técnica do Jogo")

        chutes_certos = jogo["Chutes"]
        chutes_errados = jogo.get("Chutes Errados", 0)
        finalizacoes = chutes_certos + chutes_errados

        gols = int(jogo.get("Gols Marcados", 0))
        assistencias = int(jogo.get("Assistências", 0)) if "Assistências" in jogo else 0

        passes_chave = jogo["Passes-chave"]
        passes_errados = jogo.get("Passes Errados", 0)

        desarmes = jogo["Desarmes"]
        faltas = jogo["Faltas Sofridas"]

        analise = []

        # ===============================
        # ⚽ FINALIZAÇÕES
        # ===============================
        if finalizacoes > 0:
            if gols > 0:
                eficiencia = gols / finalizacoes
                if eficiencia >= 0.25:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes**, marcou **{gols} gols** com boa eficiência."
                    )
                else:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes**, marcou **{gols} gols**, mas pode melhorar a precisão."
                    )
            else:
                analise.append(
                    f"⚽ Tentou **{finalizacoes} finalizações**, mas não marcou gols."
                )

        # ===============================
        # 🎯 PASSES-CHAVE x ASSISTÊNCIA
        # ===============================
        if passes_chave > 0:
            if assistencias > 0:
                analise.append(
                    f"🎯 Criou **{passes_chave} chances**, resultando em **{assistencias} assistência(s)**."
                )
            else:
                analise.append(
                    f"🎯 Criou **{passes_chave} chances claras**, mas sem conversão em gol."
                )

        # ===============================
        # ⚠️ ERROS DE PASSE
        # ===============================
        if passes_errados > passes_chave:
            analise.append(
                "⚠️ Teve mais erros do que passes decisivos, atenção à tomada de decisão."
            )

        # ===============================
        # 🛡️ DEFESA
        # ===============================
        if desarmes >= 5:
            analise.append(
                f"🛡️ Forte presença defensiva com **{desarmes} desarmes**."
            )

        if faltas >= 4:
            analise.append(
                f"⚡ Sofreu **{faltas} faltas**, mostrando agressividade ofensiva."
            )

        analise_texto_pdf = "\n".join(analise)
        if analise_texto_pdf:
            st.markdown(
                f"""
                        <div style="
                            background:#0B1220;
                            padding:14px;
                            border-radius:12px;
                            border-left:4px solid #00E5FF;
                            margin-bottom:14px;
                        ">
                            {analise_texto_pdf.replace("\n", "<br>")}
                        </div>
                        """,
                unsafe_allow_html=True
            )

        # 🔹 SEPARADOR PREMIUM ENTRE ANÁLISE DO JOGO E TENDÊNCIA
        st.markdown(
            """
            <div style="
                height: 2px;
                margin: 28px 0 32px 0;
                background: linear-gradient(
                    to right,
                    rgba(0,229,255,0.05),
                    rgba(0,229,255,0.9),
                    rgba(0,229,255,0.05)
                );
                box-shadow: 0 0 12px rgba(0,229,255,0.6);
                border-radius: 10px;
            "></div>
            """,
            unsafe_allow_html=True
        )

        # ======================================================
        # 🧠 ZONA 1 — CONTEXTO FÍSICO PRÉ-JOGO (7 DIAS ANTERIORES)
        # ======================================================

        st.markdown("### 🧠 Contexto Físico Pré-Jogo")

        # Data do jogo selecionado
        data_jogo = jogo["Data_DT"].date()


        # Minutos jogados no jogo
        minutos_jogo = int(jogo.get("Minutos Jogados", 0))

        # Modalidade do jogo
        modalidade_jogo = jogo["Condição do Campo"]

        # ======================================================
        # ⚖️ PESOS DE CARGA FÍSICA (BASE FISIOLÓGICA)
        # ======================================================

        PESO_JOGO_MODALIDADE = {
            "Futsal": 1.4,
            "Society": 1.2,
            "Campo": 1.0
        }

        CARGA_TREINO_MODALIDADE = {
            "Futsal": 8,
            "Society": 6,
            "Campo": 6
        }

        # Peso da modalidade
        peso_modalidade = PESO_JOGO_MODALIDADE.get(modalidade_jogo, 1.0)


        # 🔥 Carga física do jogo
        carga_fisica_jogo = minutos_jogo * peso_modalidade

        # Janela fixa: 7 dias antes do jogo
        inicio_janela = data_jogo - pd.Timedelta(days=7)
        fim_janela = data_jogo - pd.Timedelta(days=1)



        # -------- SONO --------
        sono_periodo = df_sono_full.copy()
        sono_periodo["Data_DT"] = pd.to_datetime(
            sono_periodo["Data"], dayfirst=True, errors="coerce"
        )
        sono_periodo = sono_periodo[
            (sono_periodo["Data_DT"].dt.date >= inicio_janela) &
            (sono_periodo["Data_DT"].dt.date <= fim_janela)
            ]

        media_sono = None
        if not sono_periodo.empty and "Duração do Sono (h:min)" in sono_periodo.columns:
            sono_periodo["Horas"] = sono_periodo["Duração do Sono (h:min)"].apply(parse_duration_to_hours)
            media_sono = sono_periodo["Horas"].mean()

        # -------- ANÁLISE DE HORÁRIO DO SONO --------
        dias_sono = len(sono_periodo)
        dias_apos_meia_noite = 0

        if not sono_periodo.empty and "Hora Dormir" in sono_periodo.columns:
            for h in sono_periodo["Hora Dormir"]:
                hora = safe_parse_hour(h)
                if hora is not None and hora < 6:
                    dias_apos_meia_noite += 1

        texto_horario_sono = ""
        if dias_sono > 0 and dias_apos_meia_noite > 0:
            texto_horario_sono = (
                f"⏰ Dormiu após 00:00 em "
                f"<b>{dias_apos_meia_noite}</b> de <b>{dias_sono}</b> dias<br>"
            )

        # -------- TREINOS --------
        treinos_periodo = df_treinos_full.copy()
        treinos_periodo["Date_DT"] = pd.to_datetime(
            treinos_periodo["Date"], dayfirst=True, errors="coerce"
        )
        treinos_periodo = treinos_periodo[
            (treinos_periodo["Date_DT"].dt.date >= inicio_janela) &
            (treinos_periodo["Date_DT"].dt.date <= fim_janela)
            ]
        qtde_treinos = len(treinos_periodo)

        # ======================================================
        # 🎮 CARGA FÍSICA DOS JOGOS (7 DIAS ANTERIORES)
        # ======================================================

        jogos_periodo = df_jogos_full.copy()
        jogos_periodo["Data_DT"] = pd.to_datetime(
            jogos_periodo["Data"], dayfirst=True, errors="coerce"
        )

        jogos_periodo = jogos_periodo[
            (jogos_periodo["Data_DT"].dt.date >= inicio_janela) &
            (jogos_periodo["Data_DT"].dt.date <= fim_janela)
            ]

        carga_jogos = 0

        for _, j in jogos_periodo.iterrows():
            minutos = int(j.get("Minutos Jogados", 0))
            modalidade_j = j.get("Condição do Campo", "")
            peso = PESO_JOGO_MODALIDADE.get(modalidade_j, 1.0)

            carga_jogos += minutos * peso

        # ======================================================
        # 📆 LISTA DOS JOGOS CONSIDERADOS (7 DIAS)
        # ======================================================

        lista_jogos_txt = []
        total_minutos_jogos = 0

        for _, j in jogos_periodo.iterrows():
            data_fmt = j["Data_DT"].strftime("%d/%m")
            modalidade_j = j.get("Condição do Campo", "N/D")
            minutos = int(j.get("Minutos Jogados", 0))

            total_minutos_jogos += minutos

            lista_jogos_txt.append(
                f"• {data_fmt} — {modalidade_j} — {minutos} min"
            )

        st.write("DEBUG lista_jogos_txt:", lista_jogos_txt)
        st.write("DEBUG total_minutos_jogos:", total_minutos_jogos)

        # ======================================================
        # 🔵 ALERTA AUTOMÁTICO DE SEQUÊNCIA DE JOGOS
        # ======================================================

        alerta_sequencia = None

        if not jogos_periodo.empty:

            # Datas únicas dos jogos
            datas_jogos = sorted(jogos_periodo["Data_DT"].dt.date.unique())

            dias_consecutivos = 0
            for i in range(1, len(datas_jogos)):
                if (datas_jogos[i] - datas_jogos[i - 1]).days == 1:
                    dias_consecutivos += 1

            jogos_por_dia = jogos_periodo["Data_DT"].dt.date.value_counts().max()

            total_jogos = len(jogos_periodo)

            # CONDIÇÕES DE ALERTA (nível elite)
            if (
                    dias_consecutivos >= 1
                    or jogos_por_dia >= 2
                    or total_minutos_jogos >= 70
            ):
                alerta_sequencia = (
                    f"⚠️ Atenção: o atleta participou de "
                    f"<b>{total_jogos} jogo(s)</b> em "
                    f"<b>{len(datas_jogos)} dia(s)</b>, "
                    f"acumulando <b>{total_minutos_jogos} minutos</b>, "
                    f"o que exige controle da recuperação."
                )

        # ======================================================
        # 💪 CARGA FÍSICA DOS TREINOS (7 DIAS ANTERIORES)
        # ======================================================

        carga_treinos = 0

        for _, t in treinos_periodo.iterrows():
            tipo = t.get("Tipo", "")
            carga = CARGA_TREINO_MODALIDADE.get(tipo, 4)

            carga_treinos += carga

        # -------- SAÚDE --------
        df_saude = load_saude_df()
        df_saude["Data_DT"] = pd.to_datetime(
            df_saude["Data"], dayfirst=True, errors="coerce"
        )
        saude_periodo = df_saude[
            (df_saude["Data_DT"].dt.date >= inicio_janela) &
            (df_saude["Data_DT"].dt.date <= fim_janela)
            ]

        alimentacao = saude_periodo["Alimentação"].mode().iloc[0] if not saude_periodo.empty else "N/D"
        cansaco = saude_periodo["Cansaço"].mode().iloc[0] if not saude_periodo.empty else "N/D"



        # -------- STATUS NORMALIZADO DOS PILARES --------

        # 💤 SONO
        if media_sono is None:
            status_sono = ("N/D", 50, "⚪")
        elif media_sono >= 8 and dias_apos_meia_noite <= 1:
            status_sono = ("Bom", 100, "🟢")
        elif media_sono >= 7:
            status_sono = ("Irregular", 65, "🟡")
        else:
            status_sono = ("Insuficiente", 30, "🔴")

        # 💪 TREINO
        if qtde_treinos >= 4:
            status_treino = ("Bom", 100, "🟢")
        elif qtde_treinos >= 2:
            status_treino = ("Baixo", 60, "🟡")
        else:
            status_treino = ("Muito Baixo", 30, "🔴")

        # 🍽️ ALIMENTAÇÃO
        if alimentacao == "Boa":
            status_alimentacao = ("Boa", 100, "🟢")
        elif alimentacao == "Regular":
            status_alimentacao = ("Regular", 60, "🟡")
        else:
            status_alimentacao = ("Ruim", 30, "🔴")

        # 🥵 CANSAÇO
        if cansaco == "Baixo":
            status_cansaco = ("Controlado", 100, "🟢")
        elif cansaco == "Médio":
            status_cansaco = ("Atenção", 60, "🟡")
        else:
            status_cansaco = ("Alto", 30, "🔴")

        # -------- FLAGS DOS PILARES --------

        sono_ruim = status_sono[1] <= 60
        sono_irregular = status_sono[1] == 65

        treino_baixo = status_treino[1] <= 40
        treino_alto = status_treino[1] >= 90

        alimentacao_ruim = status_alimentacao[1] <= 40

        cansaco_alto = status_cansaco[1] <= 40
        cansaco_moderado = status_cansaco[1] == 60

        # ======================================================
        # 🧠 INTERPRETAÇÃO INTELIGENTE (COM CARGA REAL)
        # ======================================================

        # Flags auxiliares
        sono_comprometido = (status_sono[1] <= 65)
        alimentacao_ruim_flag = (status_alimentacao[1] <= 40)
        cansaco_medio_ou_alto = (status_cansaco[1] <= 60)


        # ======================================================
        # 📊 STATUS DA CARGA FÍSICA (NORMALIZADO)
        # ======================================================

        carga_total = carga_jogos + carga_treinos + carga_fisica_jogo


        # ======================================================
        # 📊 STATUS DA CARGA FÍSICA (NORMALIZADO)
        # ======================================================

        if carga_total >= 350:
            status_carga = ("Alta", 30, "🔴")
        elif carga_total >= 180:
            status_carga = ("Moderada", 60, "🟡")
        else:
            status_carga = ("Baixa", 100, "🟢")

        # 🔹 AGORA SIM as flags
        carga_baixa = status_carga[0] == "Baixa"
        carga_moderada = status_carga[0] == "Moderada"
        carga_alta = status_carga[0] == "Alta"

        # 🔴🔴 CENÁRIO 8 — RISCO FISIOLÓGICO CRÍTICO
        if carga_alta and sono_comprometido and alimentacao_ruim_flag and status_cansaco[1] <= 40:
            interpretacao = (
                "🚨🚨 O contexto físico pré-jogo indica risco fisiológico crítico, com carga elevada, "
                "sono comprometido, alimentação inadequada e alto nível de cansaço. "
                "Há forte indicativo de sobrecarga e maior risco de queda de desempenho ou lesão."
            )

        # 🔴 CENÁRIO 7 — SOBRECARGA INSTALADA
        elif carga_alta and cansaco_medio_ou_alto:
            interpretacao = (
                "🚨 O atleta apresenta sinais consistentes de sobrecarga física, "
                "com carga acumulada elevada nos últimos dias e fadiga perceptível. "
                "Recomenda-se controle rigoroso da minutagem e da intensidade."
            )

        # 🟠 CENÁRIO 6 — SOBRECARGA EM CONSTRUÇÃO
        elif carga_moderada and sono_comprometido and cansaco_medio_ou_alto:
            interpretacao = (
                "⚠️ O contexto físico pré-jogo sugere início de acúmulo de carga, "
                "associado a recuperação incompleta e aumento progressivo do cansaço. "
                "Atenção à gestão de esforço."
            )

        # 🟠 CENÁRIO 5 — RECUPERAÇÃO DEFICIENTE
        elif carga_baixa and sono_comprometido:
            interpretacao = (
                "⚠️ Apesar da baixa carga física recente, o padrão de sono indica "
                "recuperação insuficiente, o que pode impactar o rendimento em jogo."
            )

        # 🟡 CENÁRIO 4 — ALERTA LEVE
        elif sono_comprometido or alimentacao_ruim_flag:
            interpretacao = (
                "⚠️ Foram observadas pequenas irregularidades no período pré-jogo, "
                "que merecem atenção para manutenção da performance."
            )

        # 🟢 CENÁRIO 1 — CONTEXTO EQUILIBRADO
        else:
            interpretacao = (
                "✅ O atleta apresentou um contexto físico equilibrado no período pré-jogo, "
                "com boa gestão de carga, recuperação adequada e condições favoráveis de desempenho."
            )

        # -------- CARD VISUAL --------
        st.markdown(
            f"""
            <div style="
                background:#0B1220;
                padding:16px;
                border-radius:14px;
                border-left:6px solid #FF9800;
                box-shadow: 0 6px 18px rgba(0,0,0,0.4);
            ">
                <strong>Baseado nos 7 dias anteriores ao jogo</strong><br><br>

                <b>📆 Jogos considerados:</b><br>
                {"<br>".join(lista_jogos_txt) if lista_jogos_txt else "Nenhum jogo registrado no período."}<br><br>

                ⏱️ <b>Minutagem acumulada:</b> {total_minutos_jogos} min<br>
                🎮 <b>Total de jogos:</b> {len(lista_jogos_txt)}<br><br>

                😴 Sono médio: <b>{f"{media_sono:.1f}h" if media_sono else "N/D"}</b><br>
                {texto_horario_sono}
                💪 Treinos: <b>{qtde_treinos}</b><br>
                🍽️ Alimentação: <b>{alimentacao}</b><br>
                🥵 Cansaço: <b>{cansaco}</b><br><br>

                {alerta_sequencia + "<br><br>" if alerta_sequencia else ""}
                <em>{interpretacao}</em>
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- VISUAL MODERNO DOS 4 PILARES --------
        st.markdown("#### 📊 Leitura Rápida do Contexto Físico")


        def barra(label, status):
            nome, valor, emoji = status
            st.markdown(
                f"""
                <div style="margin-bottom:10px;">
                    <strong>{label}</strong> {emoji} <span style="opacity:0.7;">({nome})</span>
                    <div style="background:#1F2933; border-radius:10px; overflow:hidden; height:10px;">
                        <div style="
                            width:{valor}%;
                            background:linear-gradient(90deg, #00E5FF, #1DE9B6);
                            height:10px;
                        "></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


        barra("😴 Sono", status_sono)
        barra("💪 Treino", status_treino)
        barra("🍽️ Alimentação", status_alimentacao)
        barra("🥵 Cansaço", status_cansaco)

        st.markdown(
            """
            <div style="
                height: 2px;
                margin: 28px 0 32px 0;
                background: linear-gradient(
                    to right,
                    rgba(0,229,255,0.05),
                    rgba(0,229,255,0.9),
                    rgba(0,229,255,0.05)
                );
                box-shadow: 0 0 12px rgba(0,229,255,0.6);
                border-radius: 10px;
            "></div>
            """,
            unsafe_allow_html=True
        )

        # ======================================================
        # 📈 TENDÊNCIA RECENTE (ÚLTIMOS 5 JOGOS) — ANÁLISE REAL
        # ======================================================

        # Modalidade do jogo selecionado
        modalidade_jogo = jogo["Condição do Campo"]

        st.markdown(
            f"### 📈 Tendência Recente — {modalidade_jogo} (Últimos 5 Jogos)"
        )

        # Filtra SOMENTE jogos da mesma modalidade
        df_tend = df_jogos_full[
            df_jogos_full["Condição do Campo"] == modalidade_jogo
            ].copy()

        if not df_tend.empty and len(df_tend) >= 5:

            df_tend["Data_DT"] = pd.to_datetime(
                df_tend["Data"], dayfirst=True, errors="coerce"
            )

            df_tend = df_tend.sort_values("Data_DT")

            # 👉 Score técnico por jogo
            df_tend["Score_Jogo"] = df_tend.apply(calcular_score_jogo, axis=1)

            # 🔍 Últimos 5 jogos (ordem cronológica)
            scores = df_tend.tail(5)["Score_Jogo"].values.tolist()

            ultimo = scores[-1]
            penultimo = scores[-2]
            antepenultimo = scores[-3]
            media_5 = sum(scores) / len(scores)

            jogos_ruins = sum(1 for s in scores if s < 4.5)
            jogos_bons = sum(1 for s in scores if s >= 6)

            queda_continua = ultimo < penultimo < antepenultimo
            subida_continua = ultimo > penultimo > antepenultimo

            oscilacao = (
                    max(scores) - min(scores) >= 3
                    and not subida_continua
                    and not queda_continua
            )
            # ===============================
            # 🎯 CLASSIFICAÇÃO DE NÍVEL TÉCNICO
            # ===============================

            if media_5 >= 8:
                nivel_label = "🔵 Rendimento altíssimo"
            elif media_5 >= 6:
                nivel_label = "🟢 Rendimento bom"
            elif media_5 >= 4.5:
                nivel_label = "🟠 Rendimento regular"
            else:
                nivel_label = "🔴 Rendimento baixo"

            # ===============================
            # 🧭 CLASSIFICAÇÃO DE FORMA
            # ===============================

            # 🟢 ALTA PERFORMANCE
            if media_5 >= 8 and jogos_bons >= 3 and ultimo >= 7:
                forma_label = "🟢 Alta performance"
                forma_cor = "#2E7D32"
                forma_texto = (
                    "O atleta vive um momento de alto rendimento técnico, "
                    "com atuações consistentes e impacto elevado nas partidas recentes."
                )

            # 🔴 QUEDA TÉCNICA
            elif media_5 < 4.5 and jogos_ruins >= 3 and queda_continua:
                forma_label = "🔴 Queda técnica"
                forma_cor = "#C62828"
                forma_texto = (
                    "O desempenho técnico apresenta queda progressiva nos jogos mais recentes, "
                    "indicando uma fase de baixo rendimento."
                )

            # 📈 EVOLUÇÃO
            elif subida_continua and ultimo >= media_5 and media_5 >= 4.5:
                forma_label = "⬆️ Em evolução técnica"
                forma_cor = "#00E676"
                forma_texto = (
                    "Apesar de oscilações anteriores, o atleta demonstra melhora contínua "
                    "no desempenho técnico recente."
                )

            # 🎢 OSCILAÇÃO
            elif oscilacao:
                forma_label = "➡️ Oscilação técnica"
                forma_cor = "#FFC107"
                forma_texto = (
                    "O desempenho recente apresenta variações significativas, "
                    "alternando jogos de bom nível com quedas técnicas."
                )

            # ➡️ ESTÁVEL (SOMENTE SE NÃO FOR RUIM)
            elif media_5 >= 4.5:
                forma_label = "➡️ Estável"
                forma_cor = "#9E9E9E"
                forma_texto = (
                    "O atleta mantém um padrão técnico relativamente constante, "
                    "sem grandes variações no desempenho recente."
                )

            # 🔴 RUIM SEM QUEDA CONTÍNUA
            else:
                forma_label = "🔴 Baixo rendimento"
                forma_cor = "#B71C1C"
                forma_texto = (
                    "O atleta apresenta desempenho técnico abaixo do esperado nos jogos recentes, "
                    "mesmo sem uma tendência clara de recuperação."
                )

            # 🧱 CARD VISUAL FINAL
            st.markdown(
                f"""
                        <div style="
                            padding:16px;
                            border-radius:14px;
                            background:#0B1220;
                            border-left:6px solid {forma_cor};
                            box-shadow: 0 6px 18px rgba(0,0,0,0.4);
                        ">
                            <div style="font-size:18px; font-weight:bold;">
                                {forma_label}
                            </div>
                            <div style="font-size:15px; margin-top:6px;">
                                <strong>{nivel_label}</strong>
                            </div>
                            <div style="font-size:14px; opacity:0.9; margin-top:6px;">
                                {forma_texto}
                            </div>
                        </div>
                        """,
                unsafe_allow_html=True
            )

        else:
            st.info(
                f"Dados insuficientes para análise de tendência em **{modalidade_jogo}** "
                "(mínimo 5 jogos)."
            )

        st.write("")

        # ======================================================
        # 📋 VISUALIZAÇÃO DOS ÚLTIMOS 5 JOGOS (SUPORTE À TENDÊNCIA)
        # ======================================================

        st.markdown("#### 📋 Jogos considerados na análise")

        df_ultimos_5 = df_tend.tail(5).copy()

        df_ultimos_5["Jogo"] = (
                df_ultimos_5["Casa"].astype(str) +
                " x " +
                df_ultimos_5["Visitante"].astype(str)
        )

        df_ultimos_5["Data_fmt"] = df_ultimos_5["Data_DT"].dt.strftime("%d/%m")

        df_visual = df_ultimos_5[[
            "Data_fmt",
            "Jogo",
            "Condição do Campo",
            "Score_Jogo"
        ]].rename(columns={
            "Data_fmt": "Data",
            "Condição do Campo": "Modalidade",
            "Score_Jogo": "Nota"
        })

        df_visual["Nota"] = df_visual["Nota"].round(1)

        st.dataframe(
            df_visual,
            use_container_width=True,
            hide_index=True
        )

        # ======================================================
        # 📈 GRÁFICO DE EVOLUÇÃO DAS NOTAS (ÚLTIMOS 5 JOGOS)
        # ======================================================

        st.markdown("#### 📈 Evolução das notas (últimos 5 jogos)")

        # Dados já ordenados cronologicamente
        df_chart = df_ultimos_5.copy()

        df_chart["Rotulo"] = (
                df_chart["Data_DT"].dt.strftime("%d/%m") +
                " | " +
                df_chart["Casa"] +
                " x " +
                df_chart["Visitante"]
        )

        fig_notas = go.Figure()

        fig_notas.add_trace(
            go.Scatter(
                x=df_chart["Rotulo"],
                y=df_chart["Score_Jogo"],
                mode="lines+markers",
                line=dict(
                    color="#00E5FF",
                    width=3
                ),
                marker=dict(
                    size=10,
                    color=df_chart["Score_Jogo"],
                    colorscale="RdYlGn",
                    cmin=0,
                    cmax=10
                ),
                hovertemplate="Nota: %{y:.1f}<extra></extra>"
            )
        )

        fig_notas.update_layout(
            height=230,
            margin=dict(l=20, r=20, t=10, b=20),
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="white", size=12),
            yaxis=dict(
                range=[0, 10.5],
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)",
                title="Nota"
            ),
            xaxis=dict(
                showgrid=False,
                title=""
            ),
            showlegend=False
        )

        st.plotly_chart(
            fig_notas,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "scrollZoom": False
            }
        )

        if st.button("📄 Gerar PDF do Jogo"):
            img_barra = gerar_barra_pdf(jogo, scout_cols)
            img_radar = gerar_radar_pdf(jogo, scout_cols, df_jogos_full)


            caminho_pdf = gerar_pdf_jogo(
                jogo=jogo,
                score_formatado=score_formatado,
                analise_texto=analise_texto_pdf,
                img_barra=img_barra,
                img_radar=img_radar
            )

            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar PDF do Jogo",
                    data=f,
                    file_name=f"relatorio_jogo_{jogo['Data']}.pdf",
                    mime="application/pdf"
                )


    # ======================================================
    # 📊 2️⃣ MÉDIA POR JOGO
    # ======================================================
    elif modo_scout == "📊 Média por jogo":

        total_jogos = len(df_jogos_full)
        medias = df_jogos_full[scout_cols].sum() / total_jogos if total_jogos > 0 else 0

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("🥅 Chutes/jogo", round(medias["Chutes"], 2))
        c2.metric("🛡️ Desarmes/jogo", round(medias["Desarmes"], 2))
        c3.metric("🎯 Passes-chave/jogo", round(medias["Passes-chave"], 2))
        c4.metric("⚡ Faltas Sofridas/jogo", round(medias["Faltas Sofridas"], 2))
        c5.metric("🔁 Part. Indiretas/jogo", round(medias["Participações Indiretas"], 2))

        fig = px.bar(
            x=medias.index,
            y=medias.values,
            color=medias.index,
            color_discrete_map=SCOUT_COLORS,
            labels={"x": "Scout", "y": "Média por jogo"},
            title="Média de Scouts por Jogo"
        )

        fig.update_layout(
            showlegend=False,
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="white")
        )

        st.plotly_chart(fig, use_container_width=True)

    # ======================================================
    # ⚖️ 3️⃣ COMPARAÇÃO POR MODALIDADE
    # ======================================================
    elif modo_scout == "⚖️ Comparação por modalidade":

        if "Condição do Campo" not in df_jogos_full.columns:
            st.warning("Modalidade não encontrada.")
        else:
            comp = (
                df_jogos_full.groupby("Condição do Campo")[scout_cols]
                .mean()
                .reset_index()
            )

            fig = px.bar(
                comp,
                x="Condição do Campo",
                y=scout_cols,
                barmode="group",
                color_discrete_map=SCOUT_COLORS,
                title="Comparação de Scouts por Modalidade"
            )

            fig.update_layout(
                plot_bgcolor="#0E1117",
                paper_bgcolor="#0E1117",
                font=dict(color="white")
            )

            st.plotly_chart(fig, use_container_width=True)

    # 🔹 SEPARADOR PREMIUM — FIM DO RELATÓRIO DO JOGO
    st.markdown(
        """
        <div style="
            height: 2px;
            margin: 40px 0 40px 0;
            background: linear-gradient(
                to right,
                rgba(0,229,255,0.05),
                rgba(0,229,255,0.9),
                rgba(0,229,255,0.05)
            );
            box-shadow: 0 0 14px rgba(0,229,255,0.6);
            border-radius: 10px;
        "></div>
        """,
        unsafe_allow_html=True
    )

    # =============================
    # 🌙 SONO DIÁRIO (COM FILTRO PRÓPRIO)
    # =============================
    st.markdown("### 🌙 Sono Diário")
    st.markdown("#### 🔍 Filtro de Período do Sono (Gráfico)")

    col_sono_1, col_sono_2, col_sono_3 = st.columns([1, 1, 1])

    with col_sono_1:
        sono_data_inicio = st.date_input(
            "🗓️ Data inicial (sono)",
            value=(pd.to_datetime('today') - pd.Timedelta(days=7)).date(),
            key="sono_data_inicio_grafico"
        )

    with col_sono_2:
        sono_data_fim = st.date_input(
            "🗓️ Data final (sono)",
            value=pd.to_datetime('today').date(),
            key="sono_data_fim_grafico"
        )

    with col_sono_3:
        gerar_grafico_sono = st.button("📈 Gerar gráfico de sono")

    # 👇 GRÁFICO SOMENTE SE CLICAR NO BOTÃO
    if gerar_grafico_sono:

        # 🔹 USA O DATAFRAME COMPLETO (IGNORA FILTRO DE CIMA)
        df_sono_periodo = df_sono_full.copy()

        # 🔧 LIMPEZA FORÇADA DA DATA (ESSENCIAL)
        df_sono_periodo["Data"] = (
            df_sono_periodo["Data"]
            .astype(str)
            .str.strip()  # remove espaços antes/depois
            .str.replace(r"\s+", "", regex=True)  # remove espaços invisíveis
        )

        # 🔹 Converte a data
        df_sono_periodo["Data_DT"] = pd.to_datetime(
            df_sono_periodo["Data"],
            dayfirst=True,
            errors="coerce"
        )

        # 🔹 Converte duração para horas (OBRIGATÓRIO)
        if "Duração do Sono (h:min)" in df_sono_periodo.columns:
            df_sono_periodo["Duração_Horas"] = df_sono_periodo["Duração do Sono (h:min)"].apply(
                parse_duration_to_hours)

        # 🔒 REMOVE QUALQUER REGISTRO INVÁLIDO (PROTEÇÃO)
        df_sono_periodo = df_sono_periodo.dropna(
            subset=["Data_DT", "Duração_Horas"]
        )

        # 🔹 Aplica SOMENTE o filtro de baixo
        df_sono_periodo["Data_Date"] = df_sono_periodo["Data_DT"].dt.date

        df_sono_periodo = df_sono_periodo[
            (df_sono_periodo["Data_Date"] >= sono_data_inicio) &
            (df_sono_periodo["Data_Date"] <= sono_data_fim)
            ]

        if df_sono_periodo.empty:
            st.info("Não há registros de sono no período selecionado.")
        else:
            df_sono_periodo = df_sono_periodo.sort_values("Data_DT")

            fig_sono, ax_sono = plt.subplots(figsize=(12, 6))

            # 🎨 Dark Mode
            fig_sono.patch.set_facecolor('#0E1117')
            ax_sono.set_facecolor('#0E1117')
            ax_sono.tick_params(colors='white')
            ax_sono.spines['bottom'].set_color('white')
            ax_sono.spines['left'].set_color('white')

            x = range(len(df_sono_periodo))
            y = df_sono_periodo["Duração_Horas"].values

            ax_sono.plot(x, y, linestyle='--', linewidth=2, color='#2196F3')

            # 🔹 Pontos + horas
            for i, val in enumerate(y):
                if val < 6:
                    color = "red"
                elif val > 8:
                    color = "lightgreen"
                else:
                    color = "#FF9800"

                ax_sono.scatter(i, val, color=color, s=80, zorder=3)

                h = int(val)
                m = int((val - h) * 60)
                ax_sono.text(i, val + 0.15, f"{h}h{m:02d}", ha='center', color='white', fontsize=9)

            # 🔹 Média do período
            media = y.mean()
            h_med = int(media)
            m_med = int((media - h_med) * 60)

            ax_sono.axhline(
                media,
                color='#009688',
                linestyle='-',
                linewidth=1,
                label=f"Média do período ({h_med}h{m_med:02d})"
            )

            ax_sono.axhline(6, color='red', linestyle=':', linewidth=1, label='Alerta (6h)')
            ax_sono.axhline(8, color='lightgreen', linestyle=':', linewidth=1, label='Meta (8h)')

            datas = df_sono_periodo["Data_DT"].dt.strftime('%d/%m/%Y')
            ax_sono.set_xticks(x)
            ax_sono.set_xticklabels(datas, rotation=45, ha='right', color='white')

            ax_sono.set_ylabel("Duração do sono (horas)", color='white')
            ax_sono.set_title("Sono no Período Selecionado", color='white')
            ax_sono.grid(True, linestyle=':', alpha=0.3)
            ax_sono.legend(facecolor='#1F2430', edgecolor='white', labelcolor='white')

            plt.tight_layout()
            st.pyplot(fig_sono)
            plt.close(fig_sono)

            if st.button("🔄 Recarregar Dados da Planilha"):
                st.info("Forçando recarregamento dos dados...")
                st.rerun()


# Fim da seção dos logos

# Aba Análises (resumo / gráficos rápidos)

st.markdown(
    "<p style='text-align:center; color:#6B7280; font-size:13px;'>ScoutMind • Desenvolvido para evolução contínua do atleta.</p>",
    unsafe_allow_html=True
)


