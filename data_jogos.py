import pandas as pd
import streamlit as st
from firebase_db import carregar_jogos_firestore


def load_jogos_df_firestore(user_uid: str, atleta_id: str) -> pd.DataFrame:
    jogos = carregar_jogos_firestore(user_uid, atleta_id)

    if not jogos:
        return pd.DataFrame()

    dados = []

    for jogo in jogos:
        item = {}

        # ===============================
        # 🔑 DADOS DO JOGO
        # ===============================
        item["Data"] = jogo.get("Data", "")
        item["Horário"] = jogo.get("Horário", "")
        item["Campeonato"] = jogo.get("Campeonato", "")
        item["Casa"] = jogo.get("Casa", "")
        item["Visitante"] = jogo.get("Visitante", "")
        item["Quadro Jogado"] = jogo.get("Quadro Jogado", "")
        item["Local"] = jogo.get("Local", "")
        item["Condição do Campo"] = jogo.get("Condição do Campo", "")
        item["Minutos Jogados"] = int(jogo.get("Minutos Jogados", 0))
        item["Gols Marcados"] = int(jogo.get("Gols Marcados", 0))
        item["Assistências"] = int(jogo.get("Assistências", 0))
        item["Resultado"] = jogo.get("Resultado", "")
        item["Status"] = jogo.get("status", "")


        # ===============================
        # 🕒 CONTROLE
        # ===============================
        if "criado_em" in jogo:
            item["criado_em"] = jogo["criado_em"]

        dados.append(item)

    return pd.DataFrame(dados)





