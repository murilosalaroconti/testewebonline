import pandas as pd
import streamlit as st
from firebase_db import carregar_jogos_firestore

# 🔥 SCOUTS PADRÃO (ÚNICA FONTE)
SCOUT_COLUNAS = [
    "Chutes",
    "Chutes Errados",
    "Passes-chave",
    "Passes Errados",
    "Desarmes",
    "Faltas Sofridas",
    "Participações Indiretas"
]

def load_jogos_df_firestore(atleta_id: str) -> pd.DataFrame:
    user_uid = st.session_state["user_uid"]
    jogos = carregar_jogos_firestore(user_uid, atleta_id)

    if not jogos:
        return pd.DataFrame()

    dados = []

    for jogo in jogos:
        item = jogo.copy()

        # ===============================
        # 🔑 CAMPOS DIRETOS DO JOGO
        # ===============================
        item["Data"] = jogo.get("Data", "")
        item["Horário"] = jogo.get("Horário", "")
        item["Campeonato"] = jogo.get("Campeonato", "")
        item["Casa"] = jogo.get("Casa", "")
        item["Visitante"] = jogo.get("Visitante", "")
        item["Quadro Jogado"] = jogo.get("Quadro Jogado", "")
        item["Minutos Jogados"] = jogo.get("Minutos Jogados", 0)
        item["Resultado"] = jogo.get("Resultado", "")
        item["Local"] = jogo.get("Local", "")
        item["Condição do Campo"] = jogo.get("Condição do Campo", "")

        # 🔥 CAMPOS QUE ESTAVAM SUMINDO
        item["Gols Marcados"] = int(jogo.get("Gols Marcados", 0))
        item["Assistências"] = int(jogo.get("Assistências", 0))

        # ===============================
        # 🎯 SCOUT (snake_case)
        # ===============================
        scout = jogo.get("scout", {}) or {}

        item["Chutes"] = int(scout.get("chutes", 0))
        item["Chutes Errados"] = int(scout.get("chutes_errados", 0))
        item["Passes-chave"] = int(scout.get("passes_chave", 0))
        item["Passes Errados"] = int(scout.get("passes_errados", 0))
        item["Desarmes"] = int(scout.get("desarmes", 0))
        item["Faltas Sofridas"] = int(scout.get("faltas_sofridas", 0))
        item["Participações Indiretas"] = int(scout.get("participacoes_indiretas", 0))

        # timestamp (se quiser usar pra ordenação)
        if "criado_em" in jogo:
            item["criado_em"] = jogo["criado_em"]

        dados.append(item)

    return pd.DataFrame(dados)




