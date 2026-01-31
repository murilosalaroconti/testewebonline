# ================================
# 🔧 PADRÃO DE SCOUT – MOTOR V12
# ================================
SCOUT_KEYS_V12 = {
    "finalizacao_alvo": 0,
    "finalizacao_fora": 0,
    "passe_certo": 0,
    "passe_errado": 0,
    "drible_certo": 0,
    "desarme": 0,
    "perda_posse": 0,
    "falta_sofrida": 0,
    "falta_cometida": 0,
}

# ================================
# BASE POR POSIÇÃO
# ================================
BASE_POR_POSICAO_FUTSAL = {
    "Fixo": 5.1,
    "Ala": 5.3,
    "Pivô": 5.5,
}

BASE_POR_POSICAO_CAMPO = {
    "Zagueiro": 5.2,
    "Lateral": 5.3,
    "Volante": 5.4,
    "Meia": 5.5,
    "Atacante": 5.6,
}

# ================================
# PESOS FUTSAL
# ================================
PESOS_FUTSAL = {
    "Ala": {
        "drible_certo": 0.9,
        "finalizacao_alvo": 0.7,
        "finalizacao_fora": -0.4,
        "passe_certo": 0.3,
        "passe_errado": -0.6,
        "perda_posse": -0.6,
        "falta_sofrida": 0.4,
        "falta_cometida": -0.2,
        "desarme": 0.2,
    },
    "Fixo": {
        "desarme": 0.9,
        "passe_certo": 0.3,
        "passe_errado": -0.4,
        "perda_posse": -0.5,
        "finalizacao_alvo": 0.2,
        "finalizacao_fora": -0.15,
        "drible_certo": 0.1,
        "falta_sofrida": 0.1,
        "falta_cometida": -0.25,
    },
    "Pivô": {
        "finalizacao_alvo": 1.0,
        "finalizacao_fora": -0.6,
        "perda_posse": -0.7,
        "passe_certo": 0.2,
        "passe_errado": -0.4,
        "drible_certo": 0.3,
        "desarme": 0.1,
        "falta_sofrida": 0.3,
        "falta_cometida": -0.2,
    },
}

# ================================
# PESOS CAMPO
# ================================
PESOS_CAMPO = {
    "Zagueiro": {
        "desarme": 0.8,
        "passe_certo": 0.15,
        "passe_errado": -0.35,
        "perda_posse": -0.4,
        "finalizacao_alvo": 0.25,
        "finalizacao_fora": -0.3,
        "drible_certo": 0.15,
        "falta_sofrida": 0.1,
        "falta_cometida": -0.3,
    },
    "Lateral": {
        "desarme": 0.6,
        "passe_certo": 0.2,
        "passe_errado": -0.3,
        "perda_posse": -0.35,
        "drible_certo": 0.3,
        "finalizacao_alvo": 0.4,
        "finalizacao_fora": -0.35,
        "falta_sofrida": 0.2,
        "falta_cometida": -0.25,
    },
    "Volante": {
        "desarme": 0.7,
        "passe_certo": 0.25,
        "passe_errado": -0.25,
        "perda_posse": -0.3,
        "drible_certo": 0.3,
        "finalizacao_alvo": 0.4,
        "finalizacao_fora": -0.35,
        "falta_sofrida": 0.2,
        "falta_cometida": -0.3,
    },
    "Meia": {
        "drible_certo": 0.5,
        "passe_certo": 0.3,
        "passe_errado": -0.3,
        "perda_posse": -0.35,
        "finalizacao_alvo": 0.7,
        "finalizacao_fora": -0.4,
        "falta_sofrida": 0.3,
        "falta_cometida": -0.25,
    },
    "Atacante": {
        "finalizacao_alvo": 0.9,
        "finalizacao_fora": -0.5,
        "perda_posse": -0.3,
        "drible_certo": 0.4,
        "passe_certo": 0.2,
        "passe_errado": -0.3,
        "falta_sofrida": 0.3,
        "falta_cometida": -0.2,
    },
}

# ================================
# 🎯 MOTOR PRINCIPAL
# ================================
def calcular_score_v12(jogo: dict) -> float:
    modalidade = str(jogo.get("Condição do Campo", "")).strip().title()
    posicao = str(jogo.get("posição", "Ala")).strip().title()

    scout_raw = jogo.get("scout_raw") if isinstance(jogo.get("scout_raw"), dict) else jogo.get("scout", {})
    scout = {**SCOUT_KEYS_V12, **scout_raw}

    gols = int(jogo.get("Gols Marcados", 0))
    assist = int(jogo.get("Assistências", 0))

    # -------- BASE ----------
    if modalidade == "Futsal":
        base = BASE_POR_POSICAO_FUTSAL
        posicao = posicao if posicao in base else "Ala"
        pesos = PESOS_FUTSAL.get(posicao, PESOS_FUTSAL["Ala"])
    else:
        base = BASE_POR_POSICAO_CAMPO
        posicao = posicao if posicao in base else "Meia"
        pesos = PESOS_CAMPO.get(posicao, PESOS_CAMPO["Meia"])

    score = base[posicao]

    # -------- SCOUT ----------
    for key, peso in pesos.items():
        score += scout.get(key, 0) * peso

    # -------- GOLS / ASSIST ----------
    score += gols * (1.6 if modalidade == "Futsal" else 1.8)
    score += assist * (1.1 if modalidade == "Futsal" else 1.0)

    # ================================
    # 🔒 TRAVA DE DRIBLE (CAMPO)
    # ================================
    if modalidade != "Futsal":
        bonus_drible = scout["drible_certo"] * pesos.get("drible_certo", 0)
        if bonus_drible > 1.2:
            score -= (bonus_drible - 1.2)

    # ================================
    # 🔻 FINALIZAÇÃO SEM CONVERSÃO (CAMPO)
    # ================================
    if modalidade != "Futsal":
        if scout["finalizacao_alvo"] > 0 and gols == 0:
            score -= 0.3

    # -------- QUALIDADE ----------
    pos = scout["finalizacao_alvo"] + scout["drible_certo"] + scout["desarme"] + gols + assist
    neg = scout["finalizacao_fora"] + scout["perda_posse"] + scout["passe_errado"]

    total = pos + neg
    qualidade = pos / total if total > 0 else 0.5

    if modalidade == "Futsal":
        if qualidade >= 0.7:
            score += 0.4
        elif qualidade < 0.5:
            score -= 0.6
    else:
        if qualidade >= 0.65 and (gols + assist) > 0:
            score += 0.25
        elif qualidade < 0.45:
            score -= 0.35

    # ================================
    # 🔒 TRAVAS FINAIS DE REALIDADE
    # ================================

    # CAMPO → sem impacto direto não é jogo decisivo
    if modalidade != "Futsal":
        if gols == 0 and assist == 0:
            score = min(score, 7.8)

    # FUTSAL mantém teto alto por volume e impacto constante
    if modalidade == "Futsal":
        if score > 9.2:
            score = 9.2 + (score - 9.2) * 0.4

    # Limite absoluto
    score = min(score, 9.5)

    return round(max(0, min(10, score)), 1)

