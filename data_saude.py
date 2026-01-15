import pandas as pd
import streamlit as st
from firebase_db import carregar_saude_firestore

COLUNAS_SAUDE = [
    "Data",
    "Alimentação",
    "Hidratação",
    "Cansaço",
    "Observação"
]

def load_saude_df_firestore(atleta_id: str) -> pd.DataFrame:
    user_uid = st.session_state["user_uid"]

    registros = carregar_saude_firestore(user_uid, atleta_id)

    if not registros:
        return pd.DataFrame(columns=COLUNAS_SAUDE)

    dados = []

    for r in registros:
        dados.append({
            "Data": r.get("Data", ""),
            "Alimentação": r.get("Alimentação", ""),
            "Hidratação": r.get("Hidratação", ""),
            "Cansaço": r.get("Cansaço", ""),
            "Observação": r.get("Observação", "")
        })

    return pd.DataFrame(dados)
