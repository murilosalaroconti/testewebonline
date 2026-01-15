import pandas as pd
from firebase_db import carregar_treinos_firestore

def load_treinos_df_firestore(user_uid: str, atleta_id: str):
    registros = carregar_treinos_firestore(user_uid, atleta_id)

    if not registros:
        return pd.DataFrame(columns=["Treino", "Date", "Tipo"])

    dados = []

    for r in registros:
        dados.append({
            "Treino": r.get("Treino", ""),
            "Date": r.get("Date", ""),
            "Tipo": r.get("Tipo", "")
        })

    return pd.DataFrame(dados)
