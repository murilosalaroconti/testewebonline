import pandas as pd
import streamlit as st
from firebase_db import carregar_sono_firestore

COLUNAS_SONO = [
    "Data",
    "Hora Dormir",
    "Hora Acordar",
    "Duração do Sono (h:min)",
    "Duração do Cochilo",
    "Houve Cochilo"
]

def load_sono_df_firestore(atleta_id: str):
    user_uid = st.session_state["user_uid"]

    registros = carregar_sono_firestore(user_uid, atleta_id)

    if not registros:
        return pd.DataFrame(columns=COLUNAS_SONO)

    dados = []

    for r in registros:
        dados.append({
            "Data": r.get("Data", ""),
            "Hora Dormir": r.get("Hora Dormir", ""),
            "Hora Acordar": r.get("Hora Acordar", ""),
            "Duração do Sono (h:min)": r.get("Duração do Sono (h:min)", ""),
            "Duração do Cochilo": r.get(
                "Duração do Cochilo",
                r.get("Duração do Cochilo (h:min)", "0:00")
            ),
            "Houve Cochilo": r.get("Houve Cochilo", "")
        })

    return pd.DataFrame(dados)
