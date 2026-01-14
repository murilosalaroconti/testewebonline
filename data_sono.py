import pandas as pd
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
    registros = carregar_sono_firestore(atleta_id)

    if not registros:
        return pd.DataFrame(columns=COLUNAS_SONO)

    dados = []

    for r in registros:
        dados.append({
            "Data": r.get("Data", ""),
            "Hora Dormir": r.get("Hora Dormir", ""),
            "Hora Acordar": r.get("Hora Acordar", ""),
            "Duração do Sono (h:min)": r.get("Duração do Sono (h:min)", ""),
            "Duração do Cochilo": r.get("Duração do Cochilo", ""),
            "Houve Cochilo": r.get("Houve Cochilo", "")
        })

    return pd.DataFrame(dados)
