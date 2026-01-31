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
import json
from firebase_admin import firestore
from data_treinos import load_treinos_df_firestore
from firebase_db import salvar_treino_firestore
from data_sono import load_sono_df_firestore
from firebase_db import salvar_sono_firestore
from data_saude import load_saude_df_firestore
from firebase_db import salvar_saude_firestore
from firebase_db import salvar_jogo_firestore

from data_jogos import load_jogos_df_firestore
import unicodedata
from firebase_auth import (
    login_firebase,
    criar_usuario_firebase,
    verificar_trial_ativo,enviar_email_reset_senha
)
from firebase_atletas import listar_atletas, criar_atleta
from firebase_trial import get_info_trial
from data_jogos import carregar_jogos_firestore


import uuid
from firebase_admin import get_app
from firebase_db import db
from firebase_trial import get_info_trial, get_plano_usuario
from score_v12 import calcular_score_v12

# -*- coding: utf-8 -*-



# ================================================
# 🌐 URL BASE DO SCOUT AO VIVO (PWA - FIREBASE HOSTING)
# ==================================================
PWA_BASE_URL = "https://perfomance-atleta.web.app"


st.set_page_config(page_title="Registro Atleta - Web", layout="wide", initial_sidebar_state="expanded")

def tela_login():
    st.markdown(
        """
        <style>
        .login-container {
            display: flex;
            justify-content: center;      /* centro horizontal */
            align-items: flex-start;      /* topo */
            padding-top: 24px;            /* controla altura do card */
        }

        .login-card {
            background-color: #0E1117;
            padding: 24px 26px;           /* compacto */
            border-radius: 18px;
            width: 400px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.7);
            text-align: center;
        }

        .login-title {
            font-size: 28px;
            font-weight: bold;
            color: #00E5FF;
            margin-bottom: 4px;
        }

        .login-subtitle {
            font-size: 13px;
            color: #AAAAAA;
            margin-bottom: 8px;
        }

        /* 🔥 compacta rádio (Acesso) */
        section[data-testid="stRadio"] {
            margin-top: 16px !important;
            margin-bottom: 6px !important;
        }

        /* 🔥 DIMINUI ALTURA DOS INPUTS */
        div[data-baseweb="input"] input {
            height: 36px !important;          /* altura menor */
            padding: 6px 10px !important;     /* menos espaço interno */
            font-size: 14px !important;       /* texto menor */
        }

        /* 🔥 labels (Email / Senha) mais compactas */
        label {
            margin-bottom: 2px !important;
            font-size: 13px !important;
        }

        /* 🔥 espaço entre inputs */
        div[data-baseweb="input"] {
            margin-bottom: 8px !important;
        }

        /* 🔥 botão mais próximo */
        div.stButton {
            margin-top: 6px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="login-container">
            <div class="login-card">
                <div class="login-title">⚽ ScoutMind</div>
                <div class="login-subtitle">
                    Inteligência de performance esportiva
                </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    modo = st.radio(
        "Acesso",
        ["Já tenho cadastro", "Criar conta"],
        horizontal=True
    )

    email = st.text_input("Email", placeholder="seu@email.com")
    senha = st.text_input("Senha", type="password", placeholder="••••••••")

    if st.button("🔁 Esqueceu a senha?"):
        if not email:
            st.warning("Informe o email para redefinir a senha.")
        else:
            enviado = enviar_email_reset_senha(email)

            if enviado:
                st.success(
                    "📧 Enviamos um email para redefinição de senha.\n"
                    "Verifique sua caixa de entrada."
                )
            else:
                st.error("Não foi possível enviar o email. Verifique o email informado.")

    senha_confirma = None
    if modo == "Criar conta":
        senha_confirma = st.text_input(
            "Confirmar senha",
            type="password",
            placeholder="••••••••"
        )

    entrar = st.button("🔐 Entrar", use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    if entrar:
        if not email or not senha:
            st.error("Preencha email e senha")
            return False

        if modo == "Criar conta":
            if senha != senha_confirma:
                st.error("As senhas não coincidem")
                return False

            user = criar_usuario_firebase(email, senha)

            if not user:
                st.error("Erro ao criar conta (email pode já existir)")
                return False

            # ✅ CRIA TRIAL APENAS AQUI (UMA VEZ)
            criar_trial_usuario(user["uid"], user["email"])

        else:  # Já tenho cadastro
            user = login_firebase(email, senha)

            if not user:
                st.error("Usuário ou senha inválidos")
                return False

            # 🔒 VERIFICA SE TRIAL AINDA É VÁLIDO
            if not verificar_trial_ativo(user["uid"]):
                st.error("⛔ Seu período de teste expirou.")
                return False

        st.session_state["user_logado"] = True
        st.session_state["user_uid"] = user["uid"]
        st.session_state["user_email"] = user["email"]

        st.rerun()

    return False

def tela_selecao_atleta():
    st.markdown("## 👤 Selecione um Atleta")

    user_uid = st.session_state["user_uid"]
    atletas = listar_atletas(user_uid)

    if atletas:
        opcoes = {a["nome"]: a["id"] for a in atletas}

        atleta_nome = st.selectbox(
            "Atletas cadastrados",
            list(opcoes.keys())
        )

        if st.button("✅ Entrar com este atleta"):
            st.session_state["atleta_ativo"] = opcoes[atleta_nome]
            st.rerun()

        st.markdown("---")

    st.markdown("### ➕ Criar novo atleta")
    nome_novo = st.text_input("Nome do atleta")

    if st.button("Criar atleta"):
        if not nome_novo.strip():
            st.error("Digite um nome válido")
        else:
            atleta_id = criar_atleta(user_uid, nome_novo.strip())
            st.session_state["atleta_ativo"] = atleta_id
            st.rerun()

def normalizar_jogos_firestore_base(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    # 1️⃣ NORMALIZAÇÃO BRUTA ABSOLUTA
    def _limpar_coluna(c):
        c = c.strip().lower()
        c = unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode("utf-8")
        c = "".join(c.split())
        return c

    df.columns = [_limpar_coluna(c) for c in df.columns.astype(str)]

    # 2️⃣ UNIFICA DATA (qualquer variação → data)
    if "dados" in df.columns:
        df["data"] = df["dados"]
        df.drop(columns=["dados"], inplace=True)

    # 🔒 FIX DEFINITIVO PASSSES-CHAVE
    if "passeschave" in df.columns:
        df["Passes-chave"] = df["passeschave"]

    # 3️⃣ REMOVE DUPLICADAS DE VEZ
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    # 4️⃣ MAPA FINAL
    MAPA = {
        # Dados do jogo
        "casa": "Casa",
        "visitante": "Visitante",
        "data": "Data",
        "horario": "Horário",
        "campeonato": "Campeonato",
        "quadrojogado": "Quadro Jogado",
        "minutosjogados": "Minutos Jogados",
        "resultado": "Resultado",
        "local": "Local",
        "condicaodocampo": "Condição do Campo",

        # ⚽ ESTATÍSTICAS (🔴 FALTAVA ISSO)
        "golsmarcados": "Gols Marcados",
        "assistencias": "Assistências",

        # Scouts
        "chutes": "Chutes",
        "chuteserrados": "Chutes Errados",
        "desarmes": "Desarmes",
        "passeschave": "Passes-chave",
        "passeserrados": "Passes Errados",
        "faltassofridas": "Faltas Sofridas",
        "participacoesindiretas": "Participações Indiretas",
    }

    # 🔒 FIX ABSOLUTO Passes-chave (mata coluna fantasma)
    for col in df.columns:
        if col.replace("-", "").replace("-", "").lower() == "passeschave":
            df["passeschave"] = df[col]

    df = df.rename(columns=MAPA)

    # 🔒 GARANTIA FINAL – Passes-chave nunca some
    if "Passes-chave" not in df.columns:
        candidatos = [c for c in df.columns if "passeschave" in c.lower()]
        if candidatos:
            df["Passes-chave"] = df[candidatos[0]]
        else:
            df["Passes-chave"] = 0

    ORDEM_FINAL = [
        "Casa", "Visitante",
        "Data", "Horário",
        "Campeonato", "Quadro Jogado",

        "Minutos Jogados",
        "Gols Marcados",
        "Assistências",

        # 🔥 SCOUTS REAIS
        "Chutes", "Chutes Errados",
        "Passes Certos", "Passes-chave", "Passes Errados",
        "Dribles Certos", "Desarmes",
        "Faltas Sofridas", "Faltas Cometidas",
        "Perda de Posse",

        "Participações Indiretas",
        "Resultado", "Local", "Condição do Campo"
    ]

    for col in ORDEM_FINAL:
        if col not in df.columns:
            df[col] = ""

    df = df[ORDEM_FINAL]

    # 🚨 ASSERT FINAL — SE QUEBRAR, É FIRESTORE
    assert "Dados" not in df.columns, "🔥 AINDA EXISTE 'Dados'"

    return df


def ordenar_jogos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    if "criado_em" in df.columns and df["criado_em"].notna().any():
        return df.sort_values("criado_em", ascending=False)

    if "Data_DT" not in df.columns:
        df = garantir_coluna_data_dt(df)

    if "Data_DT" in df.columns:
        return df.sort_values("Data_DT", ascending=False)

    return df


# ===============================
# 🔐 SESSION STATE GLOBAL (BASE)
# ===============================
if "user_logado" not in st.session_state:
    st.session_state["user_logado"] = False

if "user_uid" not in st.session_state:
    st.session_state["user_uid"] = None

if "atleta_ativo" not in st.session_state:
    st.session_state["atleta_ativo"] = None

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "home"

if "jogo_ativo_id" not in st.session_state:
    st.session_state["jogo_ativo_id"] = None


# 3️⃣ 🔥 AGORA SIM O ATLETA EXISTE
ATLETA_ID = st.session_state["atleta_ativo"]

# 🔒 GARANTIA GLOBAL — df_sono SEMPRE EXISTE
df_sono = load_sono_df_firestore(ATLETA_ID)


if "jogo_em_andamento" not in st.session_state:
    st.session_state["jogo_em_andamento"] = False


BASE_DIR = Path(__file__).parent
# IMAGE_PATH = BASE_DIR / "imagens" / "bernardo1.jpeg"




# ----------------------
# Configurações de arquivos
# ----------------------
#EXPECTED_REGISTROS_COLUMNS = [
    #"Casa", "Visitante", "Data", "Horário", "Campeonato", "Quadro Jogado",
    #"Minutos Jogados", "Gols Marcados", "Assistências",
    #"Chutes","Chutes Errados", "Desarmes", "Passes-chave","Passes Errados", "Faltas Sofridas", "Participações Indiretas",
    #"Resultado", "Local", "Condição do Campo",
    #"Treino", "Date", "Hora"
#]

EXPECTED_SAUDE_COLUMNS = [
    "Data",
    "Alimentação",
    "Hidratação",
    "Cansaço",
    "Observação"
]

# ----------------------
OPCOES_QUADRO = ["Principal", "Reserva", "Misto", "Não Aplicável"]
# Removida OPCOES_RESULTADO pois será texto livre (ex: 4x1)
OPCOES_MODALIDADE = ["Futsal", "Campo", "Society", "Areia"] # Nova lista

POSICOES_POR_MODALIDADE = {
    "Futsal":["Ala","Pivo","Fixo"],
    "Campo":["Zagueiro","Lateral","Volante","Meia","Atacante"]
}
# ------------------------------------------------------------------

# Garantir pasta Data
DATA_DIR = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)
SCOUT_TEMP_PATH = DATA_DIR / "scout_temp.json"


def safe_int(value):
    try:
        if value is None:
            return 0
        if isinstance(value, float) and pd.isna(value):
            return 0
        return int(float(value))
    except:
        return 0

def calcular_score_real(row):
    gols = safe_int(row.get("Gols Marcados"))
    assistencias = safe_int(row.get("Assistências"))
    passes_chave = safe_int(row.get("Passes-chave"))
    desarmes = safe_int(row.get("Desarmes"))
    faltas = safe_int(row.get("Faltas Sofridas"))
    participacoes = safe_int(row.get("Participações Indiretas"))

    chutes = safe_int(row.get("Chutes"))
    chutes_errados = safe_int(row.get("Chutes Errados"))
    passes_errados = safe_int(row.get("Passes Errados"))

    erros_total = chutes_errados + passes_errados

    # ===============================
    # ⭐ SCORE TÉCNICO PURO
    # ===============================
    score = (
        gols * 2.2 +
        assistencias * 1.8 +
        passes_chave * 0.6 +
        desarmes * 0.4 +
        faltas * 0.3 -
        erros_total * 0.25
    )

    # ===============================
    # ⚖️ VOLUME OFENSIVO REAL (CONTEXTO)
    # ===============================
    finalizacoes = chutes + chutes_errados

    volume_ofensivo = (
        finalizacoes * 0.4 +
        faltas * 0.6 +
        participacoes * 0.8
    )

    # ===============================
    # ⚖️ PROTEÇÃO DE JUSTIÇA
    # ===============================
    if volume_ofensivo >= 3 and score < 5.0:
        score = 5.0

    # Reduz punição se houve iniciativa
    if volume_ofensivo >= 3:
        score += 0.3  # bônus simbólico de iniciativa

    # ===============================
    # ⚖️ AJUSTE POR MODALIDADE
    # ===============================
    modalidade = str(row.get("Condição do Campo", "")).strip()

    fator = {
        "Futsal": 1.0,
        "Society": 0.9,
        "Campo": 0.8
    }.get(modalidade, 1.0)

    # proteção contra divisão inválida
    if fator <= 0:
        fator = 1.0

    score_final = score / fator

    return round(max(0, min(10, score_final)), 1)

def garantir_score_jogo(df):
    if df.empty:
        return df

    # ⚠️ ATENÇÃO:
    # Esta função usa SCOUT LEGADO (colunas visuais).
    # O Score oficial atual é calculado via Score_V12 (scout_raw)
    # 🔒 se não tem scout, NÃO calcula score
    scout_cols = [
        "Finalização Alvo",
        "Finalização Fora",
        "Passe Certo",
        "Passe Errado",
        "Drible Certos",
        "Desarme",
        "Perda de Posse",
        "Faltas Sofridas",
        "Falta Cometida",
    ]

    # se nenhuma coluna de scout existir → usuário básico
    if not any(col in df.columns for col in scout_cols):
        return df  # 👈 sem Score_Jogo

    df = df.copy()

    # garante colunas de scout (premium)
    for col in scout_cols:
        if col not in df.columns:
            df[col] = 0

    # evita recalcular score
    if "Score_Jogo" not in df.columns:
        df["Score_Jogo"] = df.apply(calcular_score_real, axis=1)

    return df


def garantir_coluna_data_dt(df):
    if df.empty:
        return df

    df = df.copy()

    # 🔥 REMOVE QUALQUER DUPLICAÇÃO DE COLUNAS
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]

    # 🔒 PRIORIDADE DE DATA (1 fonte só)
    if "Data" in df.columns:
        base = df["Data"]

    elif "data" in df.columns:
        base = df["data"]

    elif "Date" in df.columns:
        base = df["Date"]

    else:
        df["Data_DT"] = pd.NaT
        return df

    # 🔹 CONVERSÃO SEGURA
    df["Data_DT"] = pd.to_datetime(
        base.astype(str),
        dayfirst=True,
        errors="coerce"
    )

    return df

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
        max_val = df[scout].max() if scout in df.columns else 0
        valor = jogo.get(scout, 0)
        radar_vals.append((valor / max_val) * 100 if max_val > 0 else 0)

    radar_vals += radar_vals[:1]
    labels = scout_cols + [scout_cols[0]]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(6, 6))

    ax.plot(labels, radar_vals, color="#00E5FF", linewidth=2)
    ax.fill(labels, radar_vals, color="#00E5FF", alpha=0.35)

    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")
    ax.tick_params(colors="white")

    caminho = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plt.tight_layout()
    plt.savefig(caminho, dpi=200)
    plt.close(fig)

    return caminho


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
    if df.empty or date_col not in df.columns:
        return df

    df_temp = df.copy()

    df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors="coerce")
    df_temp = df_temp.dropna(subset=[date_col])

    start_dt = pd.to_datetime(start_date)

    # 🔥 FECHA O DIA FINAL (BUG FIX)
    end_dt = (
        pd.to_datetime(end_date)
        + pd.Timedelta(days=1)
        - pd.Timedelta(seconds=1)
    )

    return df_temp[
        (df_temp[date_col] >= start_dt) &
        (df_temp[date_col] <= end_dt)
    ]



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

#FUNÇÃO DO PAINEL BASICO (DASHBOARD)
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

#FUNÇÃO DO PAINEL BASICO (DASHBOARD
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

def normalizar_data_timezone(df, coluna):
    if coluna in df.columns:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

        # 🔥 REMOVE TIMEZONE SE EXISTIR
        if df[coluna].dt.tz is not None:
            df[coluna] = df[coluna].dt.tz_localize(None)

    return df

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
        
        /* ============================
        🎯 ESTADOS INTELIGENTES
        ============================ */

        .card-neutral {{
            background-color: #475569 !important; /* cinza */
        }}
        
        .card-ok {{
            background-color: #16A34A !important; /* verde */
        }}
        
        .card-warn {{
            background-color: #F59E0B !important; /* amarelo */
        }}
        
        .card-bad {{
            background-color: #DC2626 !important; /* vermelho */
        }}
        
        /* 7. Estilo dos títulos dos gráficos e outros textos no Dark Mode */
        h3 {{
            color: #E0E0E0;
        }}
        
        /* Otimização de margens internas */
        .card-jogos > p, .card-gols > p, .card-assistencias > p, 
        .card-minutos > p, .card-treinos > p, .card-sono > p,
        .card-derrotas > p, .card-vitorias > p, .card-avaliacao > p,
        .card-engajamento > p, .card-modalidade > p, .card-media-gols > p {{
            margin: 0;
        }}
        
        .card-jogos > label, .card-gols > label, .card-assistencias > label, 
        .card-minutos > label, .card-treinos > label, .card-sono > label,
        .card-derrotas > label, .card-vitorias > label, .card-avaliacao > label,
        .card-engajamento > label, .card-modalidade > label, .card-media-gols > label {{
            margin: 0;
        }}

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

.bg-dribles {
    background: linear-gradient(135deg, #7E57C2, #512DA8);
}

.bg-faltas-cometidas {
    background: linear-gradient(135deg, #E53935, #8E0000);
}
</style>
""", unsafe_allow_html=True)


# # Sidebar com imagem e informações
# with st.sidebar:
#     st.title("Bernardo Miranda Conti")
#     st.write("✨_Tudo posso naquele que me fortalece._✨")
#     if os.path.exists(IMAGE_PATH):
#         try:
#             img = Image.open(IMAGE_PATH)
#             st.image(img, use_container_width=True)
#         except Exception:
#             st.info("Imagem presente, mas não pode ser exibida.")
#     else:
#         st.info("Coloque a imagem em 'imagens/bernardo1.jpeg' para ver a foto aqui.")
#
#     st.markdown("---")
#
#     # Título da Seção do Atleta
#     st.subheader("👤 Perfil do Atleta")
#
#     # --- LAYOUT EM 3 COLUNAS ---
#     col_dados, col_campo, col_futsal = st.columns(3)
#
#     with col_dados:
#         st.markdown("##### 🏋️ Dados Físicos")
#         # Agrupamos em markdown simples para garantir que caiba no espaço
#         st.markdown(f"**Peso:** 33 kg")
#         st.markdown(f"**Altura:** 1.32 m")
#         st.markdown(f"**Idade:** 9 anos")
#
#     with col_campo:
#         st.markdown("##### ⚽ Posições  Campo")
#         st.markdown("- M.A")
#         st.markdown("- C.A")
#         st.markdown("- P.E")
#
#     with col_futsal:
#         st.markdown("##### 🥅 Posições  Futsal")
#         st.markdown("- Ala")
#         st.markdown("- Pivô")
#
#
#     st.markdown("---")
#     st.write("📊 Desenvolvido para fins estatísticos 📊")

if not st.session_state["user_logado"]:
    tela_login()
    st.stop()

if st.session_state["user_logado"] and not st.session_state["atleta_ativo"]:
    tela_selecao_atleta()
    st.stop()

if ATLETA_ID is None:
    st.warning("Selecione ou crie um atleta para continuar.")
    st.stop()

# ===============================
# 🔥 FONTE ÚNICA DE DADOS — FIRESTORE
# ===============================

jogos = carregar_jogos_firestore(
    st.session_state["user_uid"],
    ATLETA_ID
)

df_jogos_full = pd.DataFrame(jogos)



def normalizar_scout_pwa(s):
    if not isinstance(s, dict):
        return {k: 0 for k in [
            "Chutes","Chutes Errados","Passes Certos","Passes-chave",
            "Passes Errados","Dribles Certos","Desarmes",
            "Faltas Sofridas","Faltas Cometidas","Perda de Posse"
        ]}

    return {
        "Chutes": s.get("finalizacao_alvo", 0),
        "Chutes Errados": s.get("finalizacao_fora", 0),

        # 🔒 SEMPRE BRUTO
        "Passes Certos": s.get("passe_certo", 0),

        # 🔒 NUNCA DERIVAR AQUI
        "Passes-chave": 0,

        "Passes Errados": s.get("passe_errado", 0),
        "Dribles Certos": s.get("drible_certo", 0),
        "Desarmes": s.get("desarme", 0),
        "Faltas Sofridas": s.get("falta_sofrida", 0),
        "Faltas Cometidas": s.get("falta_cometida", 0),
        "Perda de Posse": s.get("perda_posse", s.get("participacoes_indiretas", 0))
    }



def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# ===============================
# 🔥 SCOUT — PIPELINE OFICIAL
# ===============================

# 🔒 GARANTE SCOUT RAW (VEM DO FIRESTORE)
if "scout" in df_jogos_full.columns:
    df_jogos_full["scout_raw"] = df_jogos_full["scout"]
else:
    df_jogos_full["scout_raw"] = [{} for _ in range(len(df_jogos_full))]

# 🎨 NORMALIZA SCOUT PARA UI
df_jogos_full["scout_ui"] = df_jogos_full["scout_raw"].apply(normalizar_scout_pwa)

# 🧱 EXPANDE SCOUT UI EM COLUNAS VISUAIS
df_scout_ui = pd.DataFrame(df_jogos_full["scout_ui"].tolist())

df_jogos_full = pd.concat(
    [
        df_jogos_full.drop(columns=["scout", "scout_ui"], errors="ignore"),
        df_scout_ui
    ],
    axis=1
)

st.write("MEU UID:", st.session_state["user_uid"])
st.write("MEU EMAIL:", st.session_state["user_email"])


# ============================================
# 🔥 BLOQUEIO ABSOLUTO – REMOVE COLUNAS DUPLICADAS
# ============================================
df_jogos_full.columns = df_jogos_full.columns.astype(str)
df_jogos_full = df_jogos_full.loc[:, ~df_jogos_full.columns.duplicated()]



# 🛑 PROTEÇÃO
if df_jogos_full.empty:
    st.warning("Nenhum jogo carregado ainda.")
    df_jogos_full = pd.DataFrame()
else:

    # 🔥 MOSTRAR APENAS JOGOS FINALIZADOS
    if "status" in df_jogos_full.columns:
        df_jogos_full = df_jogos_full[
            (df_jogos_full["status"] == "finalizado") |
            (df_jogos_full["status"].isna())
            ]

    # 🔒 BACKUP ABSOLUTO DO SCOUT RAW (ANTES DA NORMALIZAÇÃO)
    _scoutraw_backup = df_jogos_full["scout_raw"].copy()

    # 🔥 NORMALIZA NOMES (⚠️ ESSA FUNÇÃO APAGA COLUNAS FORA DA ORDEM_FINAL)
    df_jogos_full = normalizar_jogos_firestore_base(df_jogos_full)

    # 🔥 NORMALIZAÇÃO ÚNICA E DEFINITIVA DA MODALIDADE
    df_jogos_full["Condição do Campo"] = (
        df_jogos_full["Condição do Campo"]
        .astype(str)
        .str.lower()
        .str.strip()
        .replace({
            "fut sal": "futsal",
            "futsal ": "futsal",
            "futebol de salão": "futsal",
            "campo ": "campo",
            "society ": "society"
        })
        .str.title()
    )

    # 🔒 RESTAURA SCOUT RAW (APÓS A NORMALIZAÇÃO)
    df_jogos_full["scout_raw"] = _scoutraw_backup.values


    # 🔒 BLINDAGEM APÓS NORMALIZAÇÃO (LOCAL CORRETO)
    for col in ["Data", "Casa", "Visitante"]:
        if col in df_jogos_full.columns:
            df_jogos_full[col] = (
                df_jogos_full[col]
                .astype(str)
                .str.strip()
                .replace({"nan": "", "None": ""})
            )

    # 🔥 CORREÇÃO DA MODALIDADE  ✅ AGORA NO LUGAR CERTO
    if "Condição do Campo" in df_jogos_full.columns:
        df_jogos_full["Condição do Campo"] = (
            df_jogos_full["Condição do Campo"]
            .astype(str)
            .str.strip()
            .replace({"nan": "", "None": ""})
        )

    # 🔒 GARANTE COLUNA POSIÇÃO
    if "posição" not in df_jogos_full.columns:
        df_jogos_full["posição"] = ""

    # 🔥 DATA
    df_jogos_full = garantir_coluna_data_dt(df_jogos_full)

    # 🔥 NUMÉRICOS
    SCOUT_NUM_COLS = [
        "Chutes", "Chutes Errados",
        "Passes-chave", "Passes Errados",
        "Dribles Certos", "Desarmes",
        "Faltas Sofridas", "Faltas Cometidas",
        "Perda de Posse"
    ]

    for col in SCOUT_NUM_COLS:
        if col in df_jogos_full.columns:
            df_jogos_full[col] = pd.to_numeric(
                df_jogos_full[col], errors="coerce"
            ).fillna(0)

    # 🔥 SCORE
    df_jogos_full["scout"] = df_jogos_full.get("scout", {})
    df_jogos_full = garantir_score_jogo(df_jogos_full)


    def aplicar_score_v12(df):
        if df.empty:
            return df

        df = df.copy()

        def calc(row):
            jogo = {
                "Condição do Campo": row.get("Condição do Campo"),
                "posição": row.get("posição"),
                "Gols Marcados": safe_int(row.get("Gols Marcados", 0)),
                "Assistências": safe_int(row.get("Assistências", 0)),
                # 🔥🔥🔥 PASSA O RAW PURO 🔥🔥🔥
                "scout": row.get("scout_raw", {})
            }

            return calcular_score_v12(jogo)

        df["Score_V12"] = df.apply(calc, axis=1)
        return df


    df_jogos_full = aplicar_score_v12(df_jogos_full)


#--------------------------------------------
#Pagina Home
# Página Home
if st.session_state["pagina"] == "home":

    trial_info = get_info_trial(st.session_state["user_uid"])

    if trial_info:
        if trial_info["ativo"]:
            st.markdown(
                f"""
                <style>
                    .trial-wrapper {{
                        display: flex;
                        justify-content: center;
                        margin-bottom: 20px;
                    }}
                    .trial-banner {{
                        background-color: #4A4F1D;
                        color: #F1F5C1;
                        padding: 14px 22px;
                        border-radius: 10px;
                        width: 80%;
                        max-width: 900px;
                        font-size: 15px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                        text-align: center;       /* 👈 AQUI */
                        line-height: 1.6;         /* 👈 melhora leitura */
                    }}
                </style>

                <div class="trial-wrapper">
                    <div class="trial-banner">
                        🧪 <b>Plano de Teste Ativo</b><br>
                        ⏳ Restam {trial_info['dias_restantes']} dias de acesso gratuito.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div style="
                    display:flex;
                    justify-content:center;
                    margin-top:20px;
                ">
                    <div style="
                        background-color:#3A1515;
                        color:#FFD6D6;
                        padding:16px 22px;
                        border-radius:10px;
                        width:80%;
                        max-width:900px;
                        box-shadow:0 4px 12px rgba(0,0,0,0.4);
                    ">
                        🔒 <b>Período de teste encerrado</b><br>
                        Entre em contato para continuar usando.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.stop()


    # =========================
    # 🔒 VALORES PADRÃO (ANTI-CRASH)
    # =========================
    classe_jogo = "card-neutral"
    classe_sono = "card-neutral"


    # =========================
    # 🏟️ ÚLTIMO JOGO
    # =========================
    nota_ultimo_jogo = "—"

    if not df_jogos_full.empty:
        df_jogos_ord = ordenar_jogos(df_jogos_full)

        if not df_jogos_ord.empty:
            ultimo_jogo = df_jogos_ord.iloc[0]
            nota_ultimo_jogo = ultimo_jogo.get("Score_V12", "—")
    else:
        nota_ultimo_jogo = "—"

    # 🎯 Estado do card Último Jogo
    if nota_ultimo_jogo == "—":
        classe_jogo = "card-neutral"
    else:
        try:
            nota = float(nota_ultimo_jogo)
            if nota >= 7:
                classe_jogo = "card-ok"
            elif nota >= 5:
                classe_jogo = "card-warn"
            else:
                classe_jogo = "card-bad"
        except:
            classe_jogo = "card-neutral"

    st.markdown("## 🧠 ScoutMind")
    st.markdown("### Entenda seu jogo. Evolua com inteligência.")
    st.markdown(
        "<p style='color:#9CA3AF; margin-top:-12px; font-size:14px;'>Dados que viram decisões.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # =========================
    # 📌 CARREGAR OUTROS DADOS
    # =========================
    df_treinos = load_treinos_df_firestore(
        st.session_state["user_uid"],
        ATLETA_ID
    )
    load_sono_df_firestore(ATLETA_ID)

    if "Date" in df_treinos.columns:
        df_treinos["Date_DT"] = pd.to_datetime(df_treinos["Date"], dayfirst=True, errors="coerce")

    if "Data" in df_sono.columns:
        df_sono["Data_DT"] = pd.to_datetime(df_sono["Data"], dayfirst=True, errors="coerce")

    hoje = pd.to_datetime("today").date()



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

    # 🎯 Estado do card Sono
    if sono_ontem_txt == "Sem registro":
        classe_sono = "card-neutral"
    else:
        horas = parse_duration_to_hours(
            sono_ontem_txt.replace("h", ":").replace("m", "")
        )
        if horas >= 8:
            classe_sono = "card-ok"
        elif horas >= 6:
            classe_sono = "card-warn"
        else:
            classe_sono = "card-bad"

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
        # 🎯 ESTADO DOS CARDS (HOME)
        # =========================

        # Último jogo
        if nota_ultimo_jogo == "—":
            classe_jogo = "card-neutral"
        else:
            try:
                nota = float(nota_ultimo_jogo)
                if nota >= 7:
                    classe_jogo = "card-ok"
                elif nota >= 5:
                    classe_jogo = "card-warn"
                else:
                    classe_jogo = "card-bad"
            except:
                classe_jogo = "card-neutral"

        # Sono
        if sono_ontem_txt == "Sem registro":
            classe_sono = "card-neutral"
        else:
            horas = parse_duration_to_hours(
                sono_ontem_txt.replace("h", ":").replace("m", "")
            )
            if horas >= 8:
                classe_sono = "card-ok"
            elif horas >= 6:
                classe_sono = "card-warn"
            else:
                classe_sono = "card-bad"

    # =========================
    # =========================
    # 📈 TENDÊNCIA (5 JOGOS)
    # =========================
    tendencia = "Sem dados"

    df_jogos_ord = ordenar_jogos(df_jogos_full)

    df_jogos_ord = garantir_score_jogo(df_jogos_ord)

    tendencia = "—"

    if "Score_Jogo" in df_jogos_ord.columns and len(df_jogos_ord) >= 5:
        ultimos = df_jogos_ord.head(5)["Score_Jogo"].dropna().tolist()

        if len(ultimos) >= 2:
            if ultimos[0] > ultimos[-1]:
                tendencia = "Em evolução 📈"
            elif ultimos[0] < ultimos[-1]:
                tendencia = "Queda 📉"
            else:
                tendencia = "Estável ➖"

    # =========================
    # 🎯 CARDS PRINCIPAIS
    # =========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="card-jogos {classe_jogo}">
            ⚽ Último jogo
            <p>{nota_ultimo_jogo}</p>
            <label>Nota</label>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card-sono {classe_sono}">
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

elif st.session_state["pagina"] == "jogos":


    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("⚽ Registrar Jogos")
    col1, col2 = st.columns([2, 1])


    # ----------------------------------------------------------------------
    # Pré-carregar opções dinâmicas antes do formulário
    # ----------------------------------------------------------------------
    df_temp = df_jogos_full.copy()

    # 🔥 GARANTE COLUNAS OBRIGATÓRIAS MESMO SEM JOGOS
    for col in ["Casa", "Visitante", "Campeonato", "Local"]:
        if col not in df_temp.columns:
            df_temp[col] = ""

    times_casa = df_temp["Casa"].astype(str).unique()
    times_visitante = df_temp["Visitante"].astype(str).unique()

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

        casa_sel = st.selectbox(
            "Selecione o Time Casa",
            opcoes_times_sorted,
            key="casa_sel"
        )
        st.markdown("")

        criar_novo_casa = st.checkbox("➕ Criar novo time casa")

        novo_casa_input = ""
        if criar_novo_casa:
            novo_casa_input = st.text_input(
                "Nome do novo time casa",
                placeholder="Digite o nome do time"
            )

        st.markdown("---")

        st.markdown("##### ✈️ Time Visitante")

        visitante_sel = st.selectbox(
            "Selecione o Time Visitante",
            opcoes_times_sorted,
            key="visitante_sel"
        )
        st.markdown("")

        criar_novo_visitante = st.checkbox("➕ Criar novo time visitante")

        novo_visitante_input = ""
        if criar_novo_visitante:
            novo_visitante_input = st.text_input(
                "Nome do novo time visitante",
                placeholder="Digite o nome do time visitante"
            )

        st.markdown("---")

        st.markdown("##### 🏆 Campeonato")

        campeonato_sel = st.selectbox(
            "Selecione o Campeonato",
            opcoes_campeonato,
            key="campeonato_sel"
        )
        st.markdown("")

        criar_novo_campeonato = st.checkbox("➕ Criar novo campeonato")

        novo_campeonato_input = ""
        if criar_novo_campeonato:
            novo_campeonato_input = st.text_input(
                "Nome do novo campeonato",
                placeholder="Digite o nome do campeonato"
            )

        st.markdown("---")

        st.markdown("##### 🏟️ Local")

        local_sel = st.selectbox(
            "Selecione o Local",
            opcoes_local,
            key="local_sel"
        )
        st.markdown("")

        criar_novo_local = st.checkbox("➕ Criar novo local")

        novo_local_input = ""
        if criar_novo_local:
            novo_local_input = st.text_input(
                "Nome do novo local",
                placeholder="Digite o nome do local"
            )

        st.markdown("---")

        # ===============================
        # 🧠 BASE DO JOGO (SEMPRE EXISTE)
        # ===============================
        novo_base = {
            "Casa": "",
            "Visitante": "",
            "Campeonato": "",
            "Local": "",
        }

        if casa_sel != "Selecione ou Crie Novo":
            novo_base["Casa"] = casa_sel
        elif criar_novo_casa and novo_casa_input.strip():
            novo_base["Casa"] = novo_casa_input.strip()

        if visitante_sel != "Selecione ou Crie Novo":
            novo_base["Visitante"] = visitante_sel
        elif criar_novo_visitante and novo_visitante_input.strip():
            novo_base["Visitante"] = novo_visitante_input.strip()

        if campeonato_sel != "Selecione ou Crie Novo":
            novo_base["Campeonato"] = campeonato_sel
        elif criar_novo_campeonato and novo_campeonato_input.strip():
            novo_base["Campeonato"] = novo_campeonato_input.strip()

        if local_sel != "Selecione ou Crie Novo":
            novo_base["Local"] = local_sel
        elif criar_novo_local and novo_local_input.strip():
            novo_base["Local"] = novo_local_input.strip()

        # ===============================
        # 🔒 DEFAULTS PARA SCOUT AO VIVO
        # ===============================
        if "data_jogo_tmp" not in st.session_state:
            st.session_state["data_jogo_tmp"] = datetime.today()

        if "horario_jogo_tmp" not in st.session_state:
            st.session_state["horario_jogo_tmp"] = time(20, 0)

        if "quadro_jogo_tmp" not in st.session_state:
            st.session_state["quadro_jogo_tmp"] = "Principal"

        if "modalidade_jogo_tmp" not in st.session_state:
            st.session_state["modalidade_jogo_tmp"] = "Futsal"
        


        # ------------------ FORMULÁRIO ------------------
        #SCOUT PWA
        st.markdown("### ▶️ Scout Ao Vivo")

        # SE NÃO EXISTE JOGO ATIVO → MOSTRA BOTÃO
        if st.session_state["jogo_ativo_id"] is None:

            iniciar_scout = st.button("▶️ Iniciar Scout (Premium)", use_container_width=True)

            if iniciar_scout:
                temp_id = str(uuid.uuid4())
                st.session_state["jogo_ativo_id"] = temp_id
                st.success("Scout iniciado (temporário)")
                st.rerun()

        # SE EXISTE JOGO ATIVO → MOSTRA LINK
        else:
            scout_path = f"temp_scouts/{st.session_state['jogo_ativo_id']}"
            scout_url = f"{PWA_BASE_URL}?path={scout_path}#{scout_path}"



            st.link_button(
                "📱 Abrir Scout no Celular",
                scout_url,
                use_container_width=True
            )



        st.markdown("---")
        st.markdown("### 💾 Encerrar Partida")

        if "jogo_salvo_sucesso" not in st.session_state:
            st.session_state["jogo_salvo_sucesso"] = False


        OPCAO_INVALIDA = "Selecione ou Crie Novo"


        modalidade = st.selectbox(
            "Modalidade",
            OPCOES_MODALIDADE,
            key="modalidade_jogo"
        )

        posicoes_disponiveis = POSICOES_POR_MODALIDADE.get(modalidade, [])

        posicao = st.selectbox(
            "Posição do Atleta",
            posicoes_disponiveis,
            key="posicao_jogo"
        )

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



            salvar = st.form_submit_button("💾 Salvar Jogo")

            msg_sucesso = st.empty()  # 👈 AQUI

            if salvar:
                st.session_state["data_jogo_tmp"] = data
                st.session_state["horario_jogo_tmp"] = horario

                erros = []

                # --- TIME CASA ---
                if casa_sel == OPCAO_INVALIDA and not (criar_novo_casa and novo_casa_input.strip()):
                    erros.append("Time Casa")

                # --- TIME VISITANTE ---
                if visitante_sel == OPCAO_INVALIDA and not (criar_novo_visitante and novo_visitante_input.strip()):
                    erros.append("Time Visitante")

                # --- CAMPEONATO ---
                if campeonato_sel == OPCAO_INVALIDA and not (criar_novo_campeonato and novo_campeonato_input.strip()):
                    erros.append("Campeonato")

                # --- LOCAL ---
                if local_sel == OPCAO_INVALIDA and not (criar_novo_local and novo_local_input.strip()):
                    erros.append("Local")

                #----POSIÇÃO----
                if not posicao:
                    erros.append("Posição do Atleta")

                if erros:
                    st.error(
                        "❌ Preencha corretamente:\n- " + "\n- ".join(erros)
                    )
                    st.stop()


                if not st.session_state.get("jogo_ativo_id"):
                    st.error("Nenhum scout ativo para encerrar.")
                    st.stop()

                with st.spinner("💾 Encerrando partida..."):
                    scout_temp = {}

                    scout_temp_doc = (
                        db.collection("temp_scouts")
                        .document(st.session_state["jogo_ativo_id"])
                        .get()
                    )

                    if scout_temp_doc.exists:
                        raw = scout_temp_doc.to_dict()
                        if raw and isinstance(raw.get("scout"), dict):
                            scout_temp = raw["scout"]




                    # 🔥 CRIAR JOGO DEFINITIVO
                    jogo_base = {
                        "Data": data.strftime("%d/%m/%Y"),
                        "Horário": horario.strftime("%H:%M"),
                        "Quadro Jogado": quadro,
                        "Campeonato": novo_base["Campeonato"],
                        "Casa": novo_base["Casa"],
                        "Visitante": novo_base["Visitante"],
                        "Local": novo_base["Local"],
                        "Condição do Campo": modalidade,
                        "Posição": posicao,
                        "Minutos Jogados": minutos,
                        "Gols Marcados": gols,
                        "Assistências": assistencias,
                        "Resultado": f"{gols_atleta}x{gols_adversario}",
                        "status": "finalizado",
                        "scout": scout_temp,
                        "criado_em": firestore.SERVER_TIMESTAMP
                    }

                    jogo_id = salvar_jogo_firestore(
                        st.session_state["user_uid"],
                        ATLETA_ID,
                        jogo_base
                    )



                    # 🧹 APAGAR SCOUT TEMPORÁRIO
                    db.collection("temp_scouts") \
                        .document(st.session_state["jogo_ativo_id"]) \
                        .delete()

                st.session_state["jogo_ativo_id"] = None
                st.session_state["jogo_salvo_sucesso"] = True
                st.rerun()

            if st.session_state.get("jogo_salvo_sucesso"):
                msg_sucesso.success("⚽ Jogo registrado com sucesso!")
                st.session_state["jogo_salvo_sucesso"] = False



    # ----------------------------------------------------------------------
    # COLUNA 2 - TABELA
    # ----------------------------------------------------------------------
    with col2:
        st.markdown("### 📋 Jogos Registrados (Banco de Dados)")

        if df_jogos_full.empty:
            st.info("Nenhum jogo registrado ainda.")
        else:
            df_view = ordenar_jogos(df_jogos_full).copy()

            # Limita colunas para visualização
            colunas_exibir = [
                # 🔹 Identificação
                "Data",
                "Horário",
                "Casa",
                "Visitante",

                # 🔹 Contexto
                "Campeonato",
                "Quadro Jogado",
                "Condição do Campo",
                "Local",

                # 🔹 Estatísticas principais
                "Minutos Jogados",
                "Gols Marcados",
                "Assistências",

                # 🔹 Resultado
                "Resultado",

                # 🔹 Scouts
                "Chutes",
                "Chutes Errados",
                "Passes-chave",
                "Passes Errados",
                "Desarmes",
                "Faltas Sofridas",
                "Participações Indiretas",
                "Score_v12_TESTE",
            ]

            colunas_exibir = [c for c in colunas_exibir if c in df_view.columns]

            df_view = df_view[colunas_exibir].reset_index(drop=True)
            df_view.index += 1
            df_view.insert(0, "Nº", df_view.index)

            st.dataframe(df_view, use_container_width=True, hide_index=True)

        if st.button("Exportar CSV (últimos 200)"):
            tmp = df_view.tail(200).copy()
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

elif st.session_state["pagina"] == "treinos":

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("🎯Treinos")
    df_treinos = load_treinos_df_firestore(
        st.session_state["user_uid"],
        ATLETA_ID
    )

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
                treino_firestore = {
                    "Treino": treino_final,
                    "Date": date_str,
                    "Tipo": tipo_final
                }

                salvar_treino_firestore(
                    st.session_state["user_uid"],
                    ATLETA_ID,
                    treino_firestore
                )

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

elif st.session_state["pagina"] == "sono":


    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.header("💤Controle de Sono")

    COL_DURACAO_COCHILO = "Duração do Cochilo"
    COL_HOUVE_COCHILO = "Houve Cochilo"
    # AS CONSTANTES JÁ FORAM DEFINIDAS NO TOPO. USAMOS ELAS AQUI.
    COLUNAS_COCHILO_NAMES = [COL_DURACAO_COCHILO, COL_HOUVE_COCHILO]

    # Garante que a função load_sono_df() está carregando o DF aqui
    load_sono_df_firestore(ATLETA_ID)



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

                # 🔹 CALCULAR DURAÇÃO DO SONO (EM MINUTOS)
                t1 = datetime.strptime(hora_d_str, "%H:%M")
                t2 = datetime.strptime(hora_a_str, "%H:%M")

                # Se passou da meia-noite
                if t2 < t1:
                    t2 = t2 + timedelta(days=1)

                dur_noite_td = t2 - t1
                dur_min_noite = int(dur_noite_td.total_seconds() / 60)

                # 🔹 SALVAR NO FIRESTORE
                sono_firestore = {
                    "Data": data_str,
                    "Hora Dormir": hora_d_str,
                    "Hora Acordar": hora_a_str,
                    "Duração do Sono (h:min)": format_minutes_to_h_mm(dur_min_noite),
                    "Duração do Cochilo": "0:00",
                    "Houve Cochilo": "Não"
                }

                salvar_sono_firestore(
                    st.session_state["user_uid"],
                    ATLETA_ID,
                    sono_firestore
                )

                st.success("Registro de sono salvo com sucesso!")
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
        df_sono_atualizado = load_sono_df_firestore(ATLETA_ID)


        # Garantir coluna Data como datetime
        df_sono_atualizado["Data_DT"] = pd.to_datetime(
            df_sono_atualizado["Data"], dayfirst=True, errors="coerce"
        )

        # Ordena do mais recente para o mais antigo
        df_sono_atualizado = df_sono_atualizado.sort_values(
            "Data_DT", ascending=False
        )

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
        load_sono_df_firestore(ATLETA_ID)


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

        # ===============================
        # 🔧 PREPARA DF PARA O GRÁFICO (ORDEM CORRETA)
        # ===============================
        df_sono_plot = df_sono.copy()

        # Converte Data para datetime REAL
        df_sono_plot["Data_DT"] = pd.to_datetime(
            df_sono_plot["Data"],
            dayfirst=True,
            errors="coerce"
        )

        # Remove datas inválidas
        df_sono_plot = df_sono_plot.dropna(subset=["Data_DT"])

        # Aplica filtros (MESMOS do gráfico)
        if mes_filter_s:
            df_sono_plot = df_sono_plot[
                df_sono_plot["Data_DT"].dt.month == int(mes_filter_s)
                ]

        if ano_filter:
            df_sono_plot = df_sono_plot[
                df_sono_plot["Data_DT"].dt.year == int(ano_filter)
                ]

        # 🔥 PASSO CRÍTICO — ORDENA POR DATA
        df_sono_plot = df_sono_plot.sort_values("Data_DT")

        if df_sono.empty:
            st.info("Nenhum registro de sono.")
        else:
            datas = []
            duracoes = []
            indicador_cochilo = []
            horarios_dormir = []

            for _, row in df_sono_plot.iterrows():



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

elif st.session_state["pagina"] == "saude":

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
        data_str = data_saude.strftime("%d/%m/%Y")

        saude_firestore = {
            "Data": data_str,
            "Alimentação": alimentacao,
            "Hidratação": hidratacao,
            "Cansaço": cansaco,
            "Observação": observacao
        }

        salvar_saude_firestore(
            st.session_state["user_uid"],
            ATLETA_ID,
            saude_firestore
        )

        st.success("Registro de saúde salvo com sucesso ✅")
        st.rerun()

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

    df_saude = load_saude_df_firestore(ATLETA_ID)


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

elif st.session_state["pagina"] == "dashboard":

    conclusao_avaliacao = None

    # 🔐 CONTROLE DE PLANO
    plano = get_plano_usuario(st.session_state["user_uid"])

    is_premium = (
            plano["plano"] == "premium"
            and plano["plano_ativo"] is True
    )

    if st.button("⬅️ Voltar para Início"):
        st.session_state["pagina"] = "home"
        st.rerun()

    st.markdown("## 📊 Dashboard de Performance do Atleta")
    st.markdown("---")



    df_treinos_full = load_treinos_df_firestore(
        st.session_state["user_uid"],
        ATLETA_ID
    )


    if "Date" in df_treinos_full.columns:
        df_treinos_full["Date_DT"] = pd.to_datetime(
            df_treinos_full["Date"], dayfirst=True, errors="coerce"
        )

    df_treinos_full = normalizar_data_timezone(df_treinos_full, "Date_DT")



    df_sono_full = load_sono_df_firestore(
        ATLETA_ID
    )


    if "Data" in df_sono_full.columns:
        df_sono_full["Data_DT"] = pd.to_datetime(
            df_sono_full["Data"], dayfirst=True, errors="coerce"
        )

    df_sono_full = normalizar_data_timezone(df_sono_full, "Data_DT")

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

    df_jogos_full = df_jogos_full.loc[:, ~df_jogos_full.columns.duplicated()]

    if 'Casa' in df_jogos_full.columns:
        df_jogos_full['Casa'] = (
            df_jogos_full['Casa']
            .astype(str)
            .str.strip()
            .str.title()
        )

    # ======================================================
    # 🔒 ETAPA 4 — GARANTE COLUNA POSIÇÃO (SEGURO)
    # ======================================================

    if "posição" not in df_jogos_full.columns:
        df_jogos_full["posição"] = "Ala"  # fallback seguro
    else:
        df_jogos_full["posição"] = (
            df_jogos_full["posição"]
            .fillna("Ala")
            .astype(str)
            .str.strip()
            .replace({"": "Ala", "nan": "Ala", "None": "Ala"})
        )

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

    # ======================================================
    # 🔧 NORMALIZAÇÃO DA MODALIDADE (CAMPO / FUTSAL / SOCIETY)
    # ======================================================
    if "Condição do Campo" in df_jogos_full.columns:
        df_jogos_full["Condição do Campo"] = (
            df_jogos_full["Condição do Campo"]
            .astype(str)
            .str.strip()
            .str.title()
            .replace({
                "Campo ": "Campo",
                "Fut Sal": "Futsal",
                "Society ": "Society",
                "Nan": ""
            })
        )

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

    df_jogos_f = filter_df_by_date(df_jogos_full, 'Data_DT', data_inicio, data_fim)
    df_treinos_f = filter_df_by_date(df_treinos_full, 'Date_DT', data_inicio, data_fim)
    df_sono_f = filter_df_by_date(df_sono_full, 'Data', data_inicio, data_fim)

    df_jogos_f = garantir_score_jogo(df_jogos_f)
    df_jogos_f = aplicar_score_v12(df_jogos_f)

    # ======================================================
    # ⚖️ AJUSTE DE SCORE POR MODALIDADE (CAMPO)
    # ======================================================
    if "Condição do Campo" in df_jogos_f.columns and "Score_V12" in df_jogos_f.columns:
        ajuste_modalidade = {
            "Futsal": 1.0,  # referência
            "Society": 1.05,  # leve ajuste
            "Campo": 1.15  # compensação por menos ações
        }

        df_jogos_f["Score_V12"] = df_jogos_f.apply(
            lambda row: round(
                row["Score_V12"] * ajuste_modalidade.get(
                    str(row["Condição do Campo"]).strip().title(), 1.0
                ),
                2
            ),
            axis=1
        )

    if not df_jogos_f.empty:
        df_jogos_f = df_jogos_f.sort_values("Data_DT")
        score_dashboard = round(df_jogos_f.iloc[-1]["Score_V12"], 1)
    else:
        score_dashboard = 0

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
    # ======================================================
    # ✅ TREINOS — LÓGICA CORRETA (SEM TIME)
    # ======================================================

    df_treinos_calculo = df_treinos_f.copy()

    # 🔹 FILTRO APENAS POR MODALIDADE (TREINO NÃO TEM TIME)
    if modalidade_filter != "Todos" and 'Tipo' in df_treinos_calculo.columns:
        df_treinos_calculo['Tipo'] = (
            df_treinos_calculo['Tipo']
            .astype(str)
            .str.strip()
            .str.title()
        )

        df_treinos_calculo = df_treinos_calculo[
            df_treinos_calculo['Tipo'] == modalidade_filter
            ]

    # 🔢 TOTAL FINAL DE TREINOS
    total_treinos_display = len(df_treinos_calculo)

    # 🏷️ LABEL DO CARD
    if modalidade_filter != "Todos":
        treino_label = f"Treinos ({modalidade_filter})"
    else:
        treino_label = "Sessões Concluídas"

    # ================================
    # ⭐ AVALIAÇÃO TÉCNICA (DASHBOARD)
    # ================================
    # Baseada no PERÍODO / FILTROS (não scout, não último jogo)

    avaliacao_tecnica, conclusao_avaliacao = calculate_avaliacao_tecnica(
        df_jogos_f, modalidade_filter, time_filter
    )

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

    # 🔒 GARANTE ENGAGEMENT SEMPRE DEFINIDO
    engajamento = calculate_engajamento(
        df_treinos_f,
        df_sono_f,
        total_dias_periodo,
        media_sono_decimal
    )

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
                <label>Período Selecionado</label>
            </div>
        ''', unsafe_allow_html=True)

    # Coluna 12: Engajamento
    with col12:
        st.markdown(f'''
            <div class="card-minutos">
                🧠 ENGAJAMENTO<p>{engajamento}</p>
                <label>Sono e Disciplina</label>
            </div>
        ''', unsafe_allow_html=True)

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
        if time_filter != "Todos" and 'Treino' in df_treinos_grafico.columns:
            termo = time_filter.strip().lower()
            df_treinos_grafico = df_treinos_grafico[
                df_treinos_grafico['Treino'].astype(str).str.lower().str.contains(termo, na=False)
            ]

        # 2. FILTRO POR MODALIDADE (CORRETO E EXATO)
        if modalidade_filter != "Todos" and 'Tipo' in df_treinos_grafico.columns:
            df_treinos_grafico['Tipo'] = (
                df_treinos_grafico['Tipo']
                .astype(str)
                .str.strip()
                .str.title()
            )

            df_treinos_grafico = df_treinos_grafico[
                df_treinos_grafico['Tipo'] == modalidade_filter
                ]
        #--------------------------------------------------------------

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

    #INICIO PLANO PREMIUMM #########################################################################################

    # ======================================================
    # 🔒 BLOQUEIO DE CONTEÚDO PREMIUM
    # ======================================================

    if not is_premium:
        st.markdown("---")
        st.warning(
            "🔒 Recursos avançados disponíveis apenas no **Plano Premium**.\n\n"
            "Desbloqueie análise de scouts, score, relatórios, contexto físico e muito mais."
        )
        st.stop()

    st.markdown("---")

    # ===============================================
    # 🎨 Paleta FIFA
    SCOUT_COLORS = {
        "Chutes": "#00E5FF",
        "Chutes Errados": "#FF1744",
        "Desarmes": "#7C4DFF",
        "Passes Certos": "#00E676",
        "Passes Errados": "#9E9E9E",
        "Faltas Sofridas": "#FF9100",
        "Faltas Cometidas": "#E53935",
        "Dribles Certos": "#7E57C2",
        "Perda de Posse": "#FF5252"
    }

    # 📐 ORDEM OFICIAL DE SCOUTS (UI GLOBAL)
    SCOUT_ORDER_UI = [
        "Chutes",
        "Chutes Errados",
        "Passes Certos",
        "Passes Errados",
        "Desarmes",
        "Dribles Certos",
        "Faltas Sofridas",
        "Faltas Cometidas",
        "Perda de Posse"
    ]


    def hex_to_rgba(hex_color, alpha=0.35):
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"


    # ======================================================
    # 🔥 BASE GLOBAL DE SCOUT (RAW → COLUNAS)
    # ======================================================

    df_scout_media = df_jogos_full.copy()


    def _scout_from_raw(row):
        raw = normalizar_scout_pwa(row.get("scout_raw", {}))
        return pd.Series({k: int(raw.get(k, 0)) for k in SCOUT_ORDER_UI})


    df_scout_media[SCOUT_ORDER_UI] = (
        df_scout_media
        .apply(_scout_from_raw, axis=1)
        .fillna(0)
    )

    # 📊 ANÁLISE DE SCOUTS
    # ======================================================

    st.markdown("## 📊 Análise de Scouts")

    # Garante colunas
    scout_cols = SCOUT_ORDER_UI.copy()

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


    # =============================
    # 🔒 GARANTIA DE COLUNAS DE SCOUT NO DATAFRAME
    # =============================

    for c in SCOUT_ORDER_UI:
        if c not in df_jogos_full.columns:
            df_jogos_full[c] = 0

    df_jogos_full[SCOUT_ORDER_UI] = df_jogos_full[SCOUT_ORDER_UI].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0)

    # ======================================================
    # 🎯 1️⃣ SCOUT POR JOGO
    # ======================================================
    if modo_scout == "🎯 Scout por jogo":

        # 🔒 Garantia de Data_DT
        df_jogos_full["Data_DT"] = pd.to_datetime(
            df_jogos_full["Data"], dayfirst=True, errors="coerce"
        )

        # 🔒 Remove jogos sem data válida
        df_jogos_full = df_jogos_full.dropna(subset=["Data_DT"])

        # 🔒 Preenche Casa / Visitante ausentes
        df_jogos_full["Casa"] = (
            df_jogos_full.get("Casa", "")
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df_jogos_full["Visitante"] = (
            df_jogos_full.get("Visitante", "")
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # 🔒 Remove jogos incompletos (evita NaN x NaN)
        df_jogos_validos = df_jogos_full[
            (df_jogos_full["Casa"] != "") &
            (df_jogos_full["Visitante"] != "")
            ].copy()

        if df_jogos_validos.empty:
            st.warning("⚠️ Nenhum jogo completo disponível para análise.")
            st.stop()

        # 🔢 Ordena por data
        df_jogos_validos = df_jogos_validos.sort_values(
            "Data_DT", ascending=False
        )

        # 🏷️ Cria rótulo do jogo
        df_jogos_validos["Jogo"] = (
                df_jogos_validos["Data_DT"].dt.strftime("%d/%m/%Y") + " | " +
                df_jogos_validos["Casa"] + " x " +
                df_jogos_validos["Visitante"]
        )

        # 🎛️ Selectbox
        jogo_sel = st.selectbox(
            "Selecione o jogo:",
            df_jogos_validos["Jogo"].unique()
        )

        jogo_df = df_jogos_validos[df_jogos_validos["Jogo"] == jogo_sel]

        if jogo_df.empty:
            st.error("❌ O jogo selecionado não foi encontrado.")
            st.stop()

        jogo = jogo_df.iloc[0]

        # ======================================================
        # 🟦 RESULTADO DA PARTIDA (OFICIAL — BASEADO NO RESULTADO)
        # ======================================================

        time_casa = str(jogo.get("Casa", "Casa"))
        time_visitante = str(jogo.get("Visitante", "Visitante"))

        resultado_raw = str(jogo.get("Resultado", "")).strip().lower()

        import re

        gols_casa = gols_visitante = None

        # 🔎 Extrai placar tipo "2x1"
        match = re.search(r"(\d+)\s*x\s*(\d+)", resultado_raw)
        if match:
            gols_casa = int(match.group(1))
            gols_visitante = int(match.group(2))

        # 🎨 COR PELO RESULTADO (TIME CASA = ATLETA)
        if gols_casa is not None and gols_visitante is not None:
            if gols_casa > gols_visitante:
                cor_fundo = "#1B5E20"  # VERDE → CASA VENCEU
                texto_resultado = f"{time_casa} venceu"
            elif gols_casa < gols_visitante:
                cor_fundo = "#B71C1C"  # VERMELHO → CASA PERDEU
                texto_resultado = f"{time_casa} perdeu"
            else:
                cor_fundo = "#37474F"  # EMPATE
                texto_resultado = "Empate"

            placar = f"{time_casa} {gols_casa} x {gols_visitante} {time_visitante}"
        else:
            cor_fundo = "#263238"
            texto_resultado = "Resultado não informado"
            placar = f"{time_casa} x {time_visitante}"

        # 🧩 CARD
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {cor_fundo}, #000000);
                border-radius: 16px;
                padding: 24px;
                margin-top: 15px;
                margin-bottom: 25px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.45);
            ">
            <div style="font-size:18px; opacity:0.85; margin-bottom:6px;">
                Resultado da Partida
                </div>

            <div style="font-size:30px; font-weight:800; margin-bottom:6px;">
                {placar}
                </div>

            <div style="font-size:20px; font-weight:700;">
                {texto_resultado}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 🔒 FONTE ÚNICA DO SCOUT DO JOGO (OFICIAL)
        raw = normalizar_scout_pwa(jogo.get("scout_raw", {}))


        passes_certos_raw = int(jogo.get("scout_raw", {}).get("passe_certo", 0))
        assistencias = safe_int(jogo.get("Assistências"))

        passes_chave = assistencias
        passes_certos = passes_certos_raw  # 🔒 NÃO SUBTRAI NADA

        scout_vals = pd.Series({
            "Chutes": int(raw.get("Chutes", 0)),
            "Chutes Errados": int(raw.get("Chutes Errados", 0)),
            "Passes Certos": passes_certos,  # 🔒 BRUTO
            "Passes-chave": passes_chave,  # 🔥 DERIVADO
            "Passes Errados": int(raw.get("Passes Errados", 0)),
            "Desarmes": int(raw.get("Desarmes", 0)),
            "Dribles Certos": int(raw.get("Dribles Certos", 0)),
            "Faltas Sofridas": int(raw.get("Faltas Sofridas", 0)),
            "Faltas Cometidas": int(raw.get("Faltas Cometidas", 0)),
            "Perda de Posse": int(raw.get("Perda de Posse", 0)),
        }).reindex(scout_cols, fill_value=0)

        # ---------------- MÉTRICAS ----------------

        SCOUT_CARD_META = {
            "Chutes": ("🥅", "Chutes Certos", "bg-chutes"),
            "Chutes Errados": ("❌", "Chutes Errados", "bg-chutes-errados"),
            "Passes Certos": ("🎯", "Passes Certos", "bg-passes"),
            "Passes Errados": ("📉", "Passes Errados", "bg-passes-errados"),
            "Desarmes": ("🛡️", "Desarmes", "bg-desarmes"),
            "Dribles Certos": ("🌀", "Dribles Certos", "bg-dribles"),
            "Faltas Sofridas": ("⚡", "Faltas Sofridas", "bg-faltas"),
            "Faltas Cometidas": ("🚫", "Faltas Cometidas", "bg-faltas-cometidas"),
            "Perda de Posse": ("🔁", "Perda de Posse", "bg-indiretas"),
        }

        cards_por_linha = 5

        linhas = [
            SCOUT_ORDER_UI[i:i + cards_por_linha]
            for i in range(0, len(SCOUT_ORDER_UI), cards_por_linha)
        ]

        for linha in linhas:
            cols = st.columns(len(linha))

            for col, scout in zip(cols, linha):
                icon, label, css = SCOUT_CARD_META[scout]
                valor = int(scout_vals.get(scout, 0))

                with col:
                    st.markdown(f"""
                        <div class="scout-card {css}">
                            <div class="icon">{icon}</div>
                            <div class="scout-title">{label}</div>
                            <div class="scout-value">{valor}</div>
                        </div>
                    """, unsafe_allow_html=True)

        scout_vals_plot = scout_vals.reindex(SCOUT_ORDER_UI, fill_value=0)

        fig_barra = px.bar(
            x=scout_vals_plot.index,
            y=scout_vals_plot.values,
            color=scout_vals_plot.index,
            color_discrete_map=SCOUT_COLORS,
            text=scout_vals_plot.values,
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

        # ---------------- RADAR PREMIUM ----------------
        st.markdown("### 🎮 Radar de Scouts")

        # 📊 Ordem narrativa (ofensivo → defensivo → erros)
        radar_labels = [
            "Chutes",
            "Passes Certos",
            "Dribles Certos",
            "Faltas Sofridas",
            "Desarmes",
            "Passes Errados",
            "Perda de Posse",
            "Chutes Errados",
            "Faltas Cometidas",
        ]

        # Grupos conceituais
        positivos = {
            "Chutes",
            "Passes Certos",
            "Dribles Certos",
            "Faltas Sofridas",
            "Desarmes",
        }

        negativos = {
            "Passes Errados",
            "Perda de Posse",
            "Chutes Errados",
            "Faltas Cometidas",
        }

        # Valores reais do jogo
        valores = {k: int(scout_vals.get(k, 0)) for k in radar_labels}

        # 🔝 Normalização PELO PRÓPRIO JOGO (visual realista)
        max_jogo = max(valores.values()) if max(valores.values()) > 0 else 1

        vals_pos = [
            (valores[k] / max_jogo) * 100 if k in positivos else 0
            for k in radar_labels
        ]

        vals_neg = [
            (valores[k] / max_jogo) * 100 if k in negativos else 0
            for k in radar_labels
        ]

        fig_radar = go.Figure()

        # 🟢 POSITIVO
        fig_radar.add_trace(
            go.Scatterpolar(
                r=vals_pos,
                theta=radar_labels,
                mode="lines+markers",
                name="Ações Positivas",
                line=dict(color="#00E676", width=3),
                marker=dict(size=7, color="#00E676"),
                fill="toself",
                fillcolor="rgba(0,230,118,0.25)",
                hovertemplate="%{theta}: %{r:.0f}%<extra></extra>"
            )
        )

        # 🔴 NEGATIVO
        fig_radar.add_trace(
            go.Scatterpolar(
                r=vals_neg,
                theta=radar_labels,
                mode="lines+markers",
                name="Ações Negativas",
                line=dict(color="#FF1744", width=3),
                marker=dict(size=7, color="#FF1744"),
                fill="toself",
                fillcolor="rgba(255,23,68,0.22)",
                hovertemplate="%{theta}: %{r:.0f}%<extra></extra>"
            )
        )

        # 🎨 Layout premium
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#0E1117",
                radialaxis=dict(
                    range=[0, 100],
                    showticklabels=False,
                    ticks="",
                    gridcolor="rgba(255,255,255,0.12)"
                ),
                angularaxis=dict(
                    tickfont=dict(color="white", size=12),
                    rotation=90,
                    direction="clockwise"
                )
            ),
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            legend=dict(
                orientation="h",
                y=-0.15,
                x=0.5,
                xanchor="center"
            ),
            showlegend=True,
            height=520,
            margin=dict(t=20, b=20)
        )

        st.plotly_chart(fig_radar, use_container_width=True)

        # ======================================================
        # ======================================================
        # ⭐ SCORE GERAL DO JOGO (LÓGICA COMPLETA E REAL)
        # ======================================================

        st.markdown("### ⭐ Score Geral do Jogo")

        score_final = safe_float(jogo.get("Score_V12", 0))


        score_formatado = f"{score_final:.1f}"

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

        chutes_certos = safe_int(jogo.get("Chutes"))
        chutes_errados = safe_int(jogo.get("Chutes Errados"))
        finalizacoes = chutes_certos + chutes_errados

        gols = safe_int(jogo.get("Gols Marcados"))
        assistencias = safe_int(jogo.get("Assistências"))

        passes_chave = safe_int(jogo.get("Passes-chave"))
        passes_errados = safe_int(jogo.get("Passes Errados"))

        desarmes = safe_int(jogo.get("Desarmes"))
        faltas = safe_int(jogo.get("Faltas Sofridas"))

        analise = []

        # ===============================
        # 🔢 SCOUT ÚNICO — FONTE OFICIAL
        # ===============================

        chutes_certos = int(scout_vals.get("Chutes", 0))
        chutes_errados = int(scout_vals.get("Chutes Errados", 0))
        finalizacoes = chutes_certos + chutes_errados

        passes_certos = int(scout_vals.get("Passes Certos", 0))
        passes_chave = int(scout_vals.get("Passes-chave", 0))
        passes_errados = int(scout_vals.get("Passes Errados", 0))

        perdas_posse = int(scout_vals.get("Perda de Posse", 0))
        dribles_certos = int(scout_vals.get("Dribles Certos", 0))
        desarmes = int(scout_vals.get("Desarmes", 0))
        faltas = int(scout_vals.get("Faltas Sofridas", 0))
        faltas_cometidas = int(scout_vals.get("Faltas Cometidas", 0))

        # ===============================
        # ⚽ FINALIZAÇÕES (PRIORIDADE)
        # ===============================
        if finalizacoes > 0:
            eficiencia = gols / finalizacoes if finalizacoes > 0 else 0

            if gols >= 2:
                if eficiencia >= 0.4:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes** e marcou **{gols} gols**, com ótima eficiência."
                    )
                else:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes** e marcou **{gols} gols**, mas desperdiçou várias oportunidades."
                    )

            elif gols == 1:
                if eficiencia >= 0.3:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes** e marcou **1 gol**, com boa eficiência."
                    )
                else:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes**, marcou **1 gol**, mas precisa melhorar a precisão."
                    )

            else:  # gols == 0
                if finalizacoes >= 5:
                    analise.append(
                        f"⚽ Finalizou **{finalizacoes} vezes**, mas errou a maioria das tentativas."
                    )
                else:
                    analise.append(
                        f"⚽ Tentou **{finalizacoes} finalizações**, mas não marcou gols."
                    )

        # ===============================
        # ⚽ GARANTIA NARRATIVA DE GOLS (COM FINALIZAÇÕES)
        # ===============================
        if gols > 0 and not any("⚽" in linha for linha in analise):
            eficiencia = gols / finalizacoes if finalizacoes > 0 else 0

            if eficiencia >= 0.4:
                analise.append(
                    f"⚽ Finalizou **{finalizacoes} vezes** e marcou **{gols} gols**, mostrando boa eficiência."
                )
            else:
                analise.append(
                    f"⚽ Finalizou **{finalizacoes} vezes** e marcou **{gols} gols**, mas desperdiçou várias oportunidades."
                )

        # ===============================
        # 🎯 ASSISTÊNCIAS (FATO OBJETIVO)
        # ===============================


        passes_totais = passes_certos

        if assistencias > 0:
            analise.append(
                f"🎯 Contribuiu diretamente para o placar com **{assistencias} assistência(s)**, "
                f"sendo **{assistencias} passe(s) decisivo(s)** em um total de "
                f"**{passes_totais} passes certos**."
            )

        # ===============================
        # 🌀 DRIBLES
        # ===============================
        if dribles_certos >= 4:
            analise.append(
                "🌀 Teve sucesso nas jogadas individuais, ganhando duelos importantes."
            )
        elif dribles_certos >= 2:
            analise.append(
                "🌀 Tentou jogadas individuais em alguns momentos da partida."
            )

        # ===============================
        # 🔄 CONTROLE DE POSSE (SÓ CRÍTICA)
        # ===============================
        total_erros_posse = perdas_posse + passes_errados

        if total_erros_posse >= 7:
            analise.append(
                "🔄 Demonstrou grande instabilidade com a bola, perdendo a posse com frequência."
            )
        elif total_erros_posse >= 5:
            analise.append(
                "🔄 Oscilou no controle da posse e na tomada de decisão."
            )

        # ===============================
        # 🎯 PASSES (CONTEXTO REAL)
        # ===============================
        if passes_chave > 0 and total_erros_posse < passes_chave:
            analise.append(
                "🎯 Participou bem da construção das jogadas, dando fluidez ao jogo."
            )
        elif passes_chave > 0:
            analise.append(
                "🎯 Tentou participar da construção das jogadas, mas com eficiência irregular."
            )

        # ===============================
        # 🚨 FALTAS COMETIDAS
        # ===============================
        if faltas_cometidas >= 5:
            analise.append(
                "🚨 Cometeu muitas faltas, oferecendo bolas paradas perigosas ao adversário."
            )
        elif faltas_cometidas >= 3:
            analise.append(
                "🚨 Teve dificuldade no tempo de bola, recorrendo a faltas para conter as jogadas."
            )

        # ===============================
        # 🛡️ DEFESA
        # ===============================
        if desarmes >= 5:
            analise.append(
                f"🛡️ Forte presença defensiva, com **{desarmes} desarmes**."
            )

        if faltas >= 4:
            analise.append(
                f"⚡ Sofreu **{faltas} faltas**, mostrando intensidade e agressividade ofensiva."
            )

        # ===============================
        # 🧠 LEITURA GLOBAL DO JOGO (SEMPRE FECHA)
        # ===============================
        if score_final >= 9:
            analise.append(
                "📌 Atuação de alto nível, decisiva para o resultado da partida."
            )
        elif score_final >= 7:
            analise.append(
                "📌 Boa atuação, com contribuição relevante para a equipe."
            )
        elif score_final >= 5:
            analise.append(
                "📌 Teve impacto pontual, mas apresentou oscilações ao longo do jogo."
            )
        else:
            analise.append(
                "📌 Desempenho abaixo do ideal, com dificuldades técnicas e de tomada de decisão."
            )

        # ===============================
        # 📝 EXIBIÇÃO FINAL
        # ===============================
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

        # ======================================================
        # 🧠 ZONA 1 — CONTEXTO FÍSICO PRÉ-JOGO (7 DIAS ANTERIORES)
        # ======================================================

        st.markdown("### 🧠 Contexto Físico Pré-Jogo")


        # Data do jogo selecionado
        data_jogo = jogo["Data_DT"].date()


        # Minutos jogados no jogo
        minutos_jogo = safe_int(jogo.get("Minutos Jogados"))

        # Modalidade do jogo
        modalidade_jogo = str(jogo.get("Condição do Campo", "")).strip()

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

        treinos_por_dia = treinos_periodo["Date_DT"].dt.date.value_counts()

        qtde_treinos = treinos_por_dia.sum()
        max_treinos_no_dia = treinos_por_dia.max()

        # ======================================================
        # 🏋️ CLASSIFICAÇÃO DE VOLUME SEMANAL DE TREINOS
        # ======================================================

        if qtde_treinos >= 6:
            nivel_treino = "Excessivo"
        elif qtde_treinos == 5:
            nivel_treino = "Alto"
        else:
            nivel_treino = "Normal"

        # Flags objetivas (para o sistema)
        treino_alto = nivel_treino in ["Alto", "Excessivo"]
        treino_excessivo = nivel_treino == "Excessivo"

        # ======================================================
        # 🏋️ CARGA FÍSICA DOS TREINOS (7 DIAS) — AJUSTADA
        # ======================================================

        carga_treinos = 0

        if not treinos_periodo.empty:
            # Conta quantos treinos houve por dia
            treinos_por_dia = treinos_periodo["Date_DT"].dt.date.value_counts()

            for data, qtd in treinos_por_dia.items():
                if qtd == 1:
                    carga_treinos += 5
                elif qtd == 2:
                    carga_treinos += 8 * 2  # dois treinos no mesmo dia
                else:
                    carga_treinos += 10 * qtd  # 3 ou mais = crítico
        else:
            carga_treinos = 0

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
            minutos = safe_int(j.get("Minutos Jogados"))
            modalidade_j = str(j.get("Condição do Campo", "")).strip()
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
            minutos = safe_int(j.get("Minutos Jogados"))

            total_minutos_jogos += minutos

            lista_jogos_txt.append(
                f"• {data_fmt} — {modalidade_j} — {minutos} min"
            )



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

            max_jogos_no_dia = jogos_periodo["Data_DT"].dt.date.value_counts().max()




            total_jogos = len(jogos_periodo)

            # CONDIÇÕES DE ALERTA (nível elite)
            if (
                    dias_consecutivos >= 1
                    or max_jogos_no_dia >= 2
                    or total_minutos_jogos >= 70
            ):
                alerta_sequencia = (
                    "⚠️ Atenção: houve sequência de jogos em dias próximos, "
                    f"com <b>{total_minutos_jogos} minutos acumulados</b>. "
                    "Embora o atleta relate cansaço baixo, a exposição física recente "
                    "indica necessidade de monitoramento, pois a sobrecarga pode se "
                    "manifestar de forma tardia."
                )

            alerta_forte_carga = alerta_sequencia is not None

        # ======================================================
        # ======================================================
        # 🎮 CARGA FÍSICA DOS JOGOS (7 DIAS ANTERIORES) — AJUSTADA
        # ======================================================

        carga_jogos = 0
        jogos_por_dia = {}

        for _, j in jogos_periodo.iterrows():
            data_j = j["Data_DT"].date()
            minutos = safe_int(j.get("Minutos Jogados"))
            modalidade_j = j.get("Condição do Campo", "")
            peso = PESO_JOGO_MODALIDADE.get(modalidade_j, 1.0)

            # Conta quantos jogos já ocorreram naquele dia
            jogos_por_dia.setdefault(data_j, 0)
            jogos_por_dia[data_j] += 1

            ordem_jogo_dia = jogos_por_dia[data_j]

            # Penalidade por repetição no mesmo dia
            if ordem_jogo_dia == 1:
                fator_repeticao = 1.0
            elif ordem_jogo_dia == 2:
                fator_repeticao = 1.3  # +30%
            else:
                fator_repeticao = 1.5  # +50% (crítico)

            carga_jogos += minutos * peso * fator_repeticao



        # -------- SAÚDE --------
        df_saude = load_saude_df_firestore(ATLETA_ID)

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
        treino_alto = (
                qtde_treinos >= 5
                or max_treinos_no_dia >= 2
        )

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

        # 🔒 Garantia de existência (EVITA ERRO)
        if "alerta_forte_carga" not in locals():
            alerta_forte_carga = False

        # 🔢 Cálculo final da carga
        carga_total = carga_jogos + carga_treinos + carga_fisica_jogo

        # 🎯 Classificação objetiva da carga
        if carga_total >= 350:
            status_carga = ("Alta", 30, "🔴")
        elif carga_total >= 180:
            status_carga = ("Moderada", 60, "🟡")
        else:
            status_carga = ("Baixa", 100, "🟢")

        # 🔧 AJUSTE DE COERÊNCIA FISIOLÓGICA
        if alerta_forte_carga and status_carga[0] == "Baixa":
            status_carga = ("Moderada", 60, "🟡")

        # 🔹 FLAGS (ESSENCIAIS)
        carga_baixa = status_carga[0] == "Baixa"
        carga_moderada = status_carga[0] == "Moderada"
        carga_alta = status_carga[0] == "Alta"

        st.markdown(f"""
        <div style="
            background:#0B1220;
            padding:16px;
            border-radius:14px;
            border-left:6px solid #00E5FF;
            margin-bottom:18px;
        ">
            <strong>🧠 Contexto Físico Pré-Jogo (Dados Objetivos)</strong><br>
                Carga física estimada: <b>{status_carga[0]}</b><br>
                Sono médio (registros): <b>{status_sono[0]}</b><br>
                Sequência recente de jogos: <b>{"⚠️ Atenção" if alerta_forte_carga else "Controlada"}</b>

        </div>
        """, unsafe_allow_html=True)

        # ===============================
        # 📊 CAMADA OBJETIVA — CARGA REAL
        # ===============================

        texto_carga_real = (
            f"📈 <strong>Exposição física:</strong> "
            f"{status_carga[0]}<br>"
            f"⏱️ Minutagem acumulada: <strong>{total_minutos_jogos} min</strong><br>"
            f"💪 Treinos na semana: <strong>{qtde_treinos}</strong>"
        )

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

        # 🟠 CENÁRIO 6A — CARGA MODERADA COM SEQUÊNCIA (PRIORIDADE)
        elif carga_moderada and alerta_forte_carga:
            interpretacao = (
                "⚠️ A carga física recente foi moderada, impulsionada por jogos em dias próximos ou "
                "acúmulo de minutagem. Mesmo com cansaço controlado, a recuperação deve ser monitorada "
                "para evitar impacto no desempenho."
            )

        # 🟠 CENÁRIO 6B — SOBRECARGA EM CONSTRUÇÃO
        elif carga_moderada and sono_comprometido and cansaco_medio_ou_alto:
            interpretacao = (
                "⚠️ O contexto físico pré-jogo sugere início de acúmulo de carga, "
                "associado a recuperação incompleta e aumento progressivo do cansaço. "
                "Atenção à gestão de esforço."
            )

        # 🟠 CENÁRIO 5 — RECUPERAÇÃO DEFICIENTE (SÓ COM CARGA REALMENTE BAIXA)
        elif carga_baixa and sono_comprometido and not alerta_forte_carga:
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

        # ======================================================
        # 🧠 LEITURA DO SISTEMA — MOTIVOS OBJETIVOS
        # ======================================================

        motivos_irregularidades = []

        if sono_comprometido:
            motivos_irregularidades.append(
                "Sono com padrão irregular (horários tardios ou recuperação incompleta)"
            )

        if alerta_forte_carga:
            motivos_irregularidades.append(
                "Sequência de jogos em curto intervalo"
            )

        if treino_excessivo:
            motivos_irregularidades.append(
                "Volume semanal de treinos excessivo"
            )
        elif nivel_treino == "Alto":
            motivos_irregularidades.append(
                "Volume semanal de treinos alto"
            )

        if alimentacao_ruim_flag:
            motivos_irregularidades.append(
                "Qualidade da alimentação abaixo do ideal"
            )

        st.markdown("""
        <div style="
            background:#0B1220;
            padding:16px;
            border-radius:14px;
            border-left:6px solid #FFC107;
            margin-bottom:20px;
        ">
            <strong>🧠 Leitura do Sistema</strong><br>
            ⚠️ Irregularidades identificadas no período pré-jogo:<br><br>
            {}
        </div>
        """.format(
            "<br>".join([f"• {m}" for m in motivos_irregularidades])
            if motivos_irregularidades
            else "• Nenhuma irregularidade relevante identificada."
        ), unsafe_allow_html=True)

        # -------- CARD VISUAL --------
        html_lista_jogos = "<br>".join(lista_jogos_txt) if lista_jogos_txt else "Nenhum jogo registrado no período."

        html_card = (
            "<div style='background:#0B1220;"
            "padding:16px;"
            "border-radius:14px;"
            "border-left:6px solid #FF9800;"
            "box-shadow: 0 6px 18px rgba(0,0,0,0.4);'>"

            "<strong>📆 Baseado nos 7 dias anteriores ao jogo</strong><br><br>"

            "<strong>📆 Jogos considerados:</strong><br>"
            f"{html_lista_jogos}<br><br>"

            "<hr style='border:0.5px solid #333;'><br>"

            "<strong>🧠 Percepção do atleta (autorrelato)</strong><br>"
            f"🥵 Cansaço relatado: <strong>{cansaco}</strong><br>"
            f"🍽️ Alimentação: <strong>{alimentacao}</strong><br>"
            f"😴 Sono médio: <strong>{f'{media_sono:.1f}h' if media_sono else 'N/D'}</strong><br>"
            f"{texto_horario_sono}<br>"

            "<hr style='border:0.5px solid #333;'><br>"

            "<strong>📊 Exposição física real (dados objetivos)</strong><br>"
            f"{texto_carga_real}<br><br>"

            f"{alerta_sequencia + '<br><br>' if alerta_sequencia else ''}"

            "<strong>🧠 Conclusão do sistema</strong><br>"
            f"<em>{interpretacao}</em><br><br>"
            "</div>"
        )

        with st.expander("📊 Ver detalhes técnicos do contexto físico"):
            st.markdown(html_card, unsafe_allow_html=True)



        # -------- VISUAL MODERNO DOS 4 PILARES --------
        st.markdown("#### 📊 Leitura Rápida do Contexto Físico do Atleta (Resumo ultimos 7 dias)")


        def barra(label, status):
            nome, valor, emoji = status

            if nome.lower() in ["irregular", "atenção"]:
                gradiente = "linear-gradient(90deg, #FBBF24, #F59E0B)"  # AMARELO
            elif nome.lower() in ["alto", "ruim"]:
                gradiente = "linear-gradient(90deg, #EF4444, #B91C1C)"  # VERMELHO
            else:
                gradiente = "linear-gradient(90deg, #00E5FF, #1DE9B6)"  # BOM

            st.markdown(
                f"""
                <div style="margin-bottom:10px;">
                    <strong>{label}</strong> {emoji} <span style="opacity:0.7;">({nome})</span>
                    <div style="background:#1F2933; border-radius:10px; overflow:hidden; height:10px;">
                        <div style="
                            width:{valor}%;
                            background:{gradiente};
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
            "<span style='opacity:0.7;'>"
            "ℹ️ O cansaço representa a percepção do atleta e pode divergir da carga física estimada pelo sistema."
            "</span>",
            unsafe_allow_html=True
        )

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
        # 📈 TENDÊNCIA RECENTE (ÚLTIMOS 5 JOGOS)
        # ======================================================

        modalidade_jogo = jogo["Condição do Campo"]

        df_tend = df_jogos_full[
            df_jogos_full["Condição do Campo"] == modalidade_jogo
            ].copy()

        # 🔒 GARANTE O SCORE (AQUI É O LUGAR CERTO)
        df_tend = garantir_score_jogo(df_tend)

        if df_tend.empty or "Score_Jogo" not in df_tend.columns:
            st.info("Dados insuficientes para análise de tendência.")

        elif len(df_tend) < 5:
            st.info("São necessários pelo menos 5 jogos para análise de tendência.")

        else:
            df_tend = ordenar_jogos(df_tend)
            scores = df_tend.head(5)["Score_Jogo"].tolist()

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
            # 🎯 CLASSIFICAÇÃO DE NÍVEL
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
            # 🧭 FORMA
            # ===============================
            if media_5 >= 8 and jogos_bons >= 3 and ultimo >= 7:
                forma_label = "🟢 Alta performance"
                forma_cor = "#2E7D32"
                forma_texto = "O atleta vive um momento de alto rendimento técnico."
            elif media_5 < 4.5 and jogos_ruins >= 3 and queda_continua:
                forma_label = "🔴 Queda técnica"
                forma_cor = "#C62828"
                forma_texto = "Há queda progressiva no rendimento técnico."
            elif subida_continua:
                forma_label = "⬆️ Em evolução técnica"
                forma_cor = "#00E676"
                forma_texto = "O atleta apresenta evolução técnica recente."
            elif oscilacao:
                forma_label = "➡️ Oscilação técnica"
                forma_cor = "#FFC107"
                forma_texto = "O rendimento apresenta variações."
            else:
                forma_label = "➡️ Estável"
                forma_cor = "#9E9E9E"
                forma_texto = "O atleta mantém padrão técnico estável."

            # ✅ CARD FINAL
            st.markdown(f"""
            <div style="
                padding:16px;
                border-radius:14px;
                background:#0B1220;
                border-left:6px solid {forma_cor};
            ">
                <b>{forma_label}</b><br>
                {nivel_label}<br>
                <span style="opacity:0.8">{forma_texto}</span>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # ======================================================
        # 📋 VISUALIZAÇÃO DOS ÚLTIMOS 5 JOGOS (SUPORTE À TENDÊNCIA)
        # ======================================================

        # 🔒 SCORE UNIFICADO (V12 > Legado)
        if "Score_V12" in df_tend.columns:
            df_tend["Score_Usado"] = df_tend["Score_V12"]
        else:
            df_tend["Score_Usado"] = df_tend.get("Score_Jogo", 0)

        st.markdown("#### 📋 Jogos considerados na análise")

        df_ultimos_5 = df_tend.head(5).copy()


        df_ultimos_5["Jogo"] = (
                df_ultimos_5["Casa"].astype(str) +
                " x " +
                df_ultimos_5["Visitante"].astype(str)
        )

        df_ultimos_5["Data_fmt"] = df_ultimos_5["Data"].astype(str).str[:5]

        df_visual = df_ultimos_5[[
            "Data_fmt",
            "Jogo",
            "Condição do Campo",
            "Score_Usado"
        ]].rename(columns={
            "Data_fmt": "Data",
            "Condição do Campo": "Modalidade",
            "Score_Usado": "Nota"
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
                df_chart["Data_fmt"] +
                " | " +
                df_chart["Casa"] +
                " x " +
                df_chart["Visitante"]
        )

        fig_notas = go.Figure()

        fig_notas.add_trace(
            go.Scatter(
                x=df_chart["Rotulo"],
                y=df_chart["Score_Usado"],
                mode="lines+markers",
                line=dict(
                    color="#00E5FF",
                    width=3
                ),
                marker=dict(
                    size=10,
                    color=df_chart["Score_Usado"],
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

        medias = (
            df_scout_media[SCOUT_ORDER_UI].sum() / total_jogos
            if total_jogos > 0
            else pd.Series(0, index=SCOUT_ORDER_UI)
        )

        media_assistencias = (
            df_jogos_full["Assistências"].sum() / total_jogos
            if total_jogos > 0 else 0
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("🥅 Chutes/jogo", round(medias["Chutes"], 2))
        c2.metric("🛡️ Desarmes/jogo", round(medias["Desarmes"], 2))
        c3.metric("🎯 Assistências/jogo", round(media_assistencias, 2))
        c4.metric("⚡ Faltas Sofridas/jogo", round(medias["Faltas Sofridas"], 2))
        c5.metric("🔁 Perda de Posse/jogo", round(medias["Perda de Posse"], 2))

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
    # ⚖️ 3️⃣ COMPARAÇÃO POR MODALIDADE (MÉDIA POR JOGO)
    # ======================================================
    elif modo_scout == "⚖️ Comparação por modalidade":

        df_jogos_comp = df_scout_media.copy()

        # 📅 FILTRO DE ANO (UI)
        anos_disponiveis = (
            df_scout_media["Data_DT"]
            .dropna()
            .dt.year
            .sort_values()
            .unique()
        )

        ano_selecionado = st.selectbox(
            "📅 Selecionar ano",
            ["Todos"] + anos_disponiveis.tolist()
        )

        # 🔒 APLICA FILTRO DE ANO
        if ano_selecionado != "Todos":
            df_jogos_comp = df_jogos_comp[
                df_jogos_comp["Data_DT"].dt.year == ano_selecionado
                ]

        # 🧹 NORMALIZA CONDIÇÃO DO CAMPO
        df_jogos_comp["Condição do Campo"] = (
            df_jogos_comp["Condição do Campo"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({
                "fut sal": "futsal",
                "futsal ": "futsal",
                "campo ": "campo",
                "society ": "society"
            })
            .str.title()
        )

        # 🔒 APENAS CAMPO E FUTSAL
        df_jogos_comp = df_jogos_comp[
            df_jogos_comp["Condição do Campo"].isin(["Campo", "Futsal"])
        ]

        if df_jogos_comp.empty:
            st.info("Não há jogos suficientes para comparação.")
            st.stop()

        # 📊 CONTAGEM REAL DE JOGOS (POR DATA)
        qtd_campo = (
            df_jogos_comp[df_jogos_comp["Condição do Campo"] == "Campo"]["Data_DT"]
            .dt.date
            .nunique()
        )

        qtd_futsal = (
            df_jogos_comp[df_jogos_comp["Condição do Campo"] == "Futsal"]["Data_DT"]
            .dt.date
            .nunique()
        )

        # ✅ AGREGA SCOUT POR JOGO (PRIMEIRO)
        scout_por_jogo = (
            df_jogos_comp
            .groupby(["Data_DT", "Condição do Campo"])[SCOUT_ORDER_UI]
            .sum()
            .reset_index()
        )

        # ✅ MÉDIA POR MODALIDADE (DEPOIS)
        comp = (
            scout_por_jogo
            .groupby("Condição do Campo")[SCOUT_ORDER_UI]
            .mean()
            .reset_index()
        )

        # 🔢 SEM ESCALA (VALOR REAL = MÉDIA)
        ESCALA_VISUAL = 1
        comp[SCOUT_ORDER_UI] = comp[SCOUT_ORDER_UI] * ESCALA_VISUAL

        # 📈 GRÁFICO
        fig = px.bar(
            comp,
            x="Condição do Campo",
            y=SCOUT_ORDER_UI,
            barmode="group",
            color_discrete_map=SCOUT_COLORS,
            title="Comparação de Scouts por Modalidade (média por jogo)"
        )

        # 🔢 NÚMERO COM 1 CASA DECIMAL (CORRETO PRA MÉDIA)
        fig.update_traces(
            texttemplate="%{y:.1f}",
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(
                color="white",
                size=13
            )
        )

        fig.update_layout(
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            xaxis_title=None,
            yaxis_title=None,
            uniformtext_minsize=10,
            uniformtext_mode="hide"
        )

        # 🏷️ TEXTO EXPLICATIVO EMBAIXO DO GRÁFICO
        fig.add_annotation(
            text=f"Média por jogo • Base: {qtd_futsal} jogos Futsal • {qtd_campo} jogos Campo",
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.18,
            showarrow=False,
            font=dict(
                size=12,
                color="rgba(255,255,255,0.75)"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

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


# Fim da seção dos logos

# Aba Análises (resumo / gráficos rápidos)

st.markdown(
    "<p style='text-align:center; color:#6B7280; font-size:13px;'>ScoutMind • Desenvolvido para evolução contínua do atleta.</p>",
    unsafe_allow_html=True
)


