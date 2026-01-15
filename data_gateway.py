print("🚀 data_gateway.py FOI CARREGADO")

def carregar_jogos_normalizados(fonte="sheets"):
    EXPECTED_JOGOS_COLUMNS = [
        "Data",
        "Casa",
        "Visitante",
        "Campeonato",
        "Condição do Campo",
        "Resultado",
        "Gols Marcados",
        "Assistências",
        "Minutos Jogados"
    ]

    if fonte == "firestore":
        dados = carregar_jogos_firestore("bernardo_miranda")
        df = pd.DataFrame(dados)

        df = df.rename(columns={
            "data": "Data",
            "casa": "Casa",
            "visitante": "Visitante",
            "campeonato": "Campeonato"
        })

        if "scout" in df.columns:
            scout_df = pd.json_normalize(df["scout"])
            df = pd.concat(
                [df.drop(columns=["scout"]), scout_df],
                axis=1
            )
    else:
        df = load_registros()

    # 🔒 GARANTE TODAS AS COLUNAS
    for col in EXPECTED_JOGOS_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # 🔹 DATA ÚNICA
    df["Data_DT"] = pd.to_datetime(
        df["Data"],
        dayfirst=True,
        errors="coerce"
    )

    df = df.dropna(subset=["Data_DT"])
    df = df.sort_values("Data_DT", ascending=False)

    # 🔹 SCORE EM UM LUGAR SÓ
    df = garantir_score_jogo(df)

    return df
