
import firebase_admin
from firebase_admin import credentials, firestore


# 🔐 Inicialização ÚNICA e DEFINITIVA
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()



# ======================================================
# 📌 JOGOS
# ======================================================

def salvar_jogo_firestore(user_uid, atleta_id, jogo):
    ref = (
        db.collection("users")
        .document(user_uid)
        .collection("atletas")
        .document(atleta_id)
        .collection("jogos")
        .document()
    )
    ref.set(jogo)
    return ref.id


def carregar_jogos_firestore(user_uid: str, atleta_id: str):
    docs = (
        db.collection("users")
        .document(user_uid)
        .collection("atletas")
        .document(atleta_id)
        .collection("jogos")
        .stream()
    )

    jogos = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        jogos.append(data)

    return jogos

# ======================================================
# 📌 ENCERRAR JOGO (FINALIZA PARTIDA)
# ======================================================
def encerrar_jogo_firestore(
    user_uid: str,
    atleta_id: str,
    jogo_id: str,
    minutos: int,
    gols: int,
    assistencias: int,
    resultado: str
):
    db.collection("users") \
        .document(user_uid) \
        .collection("atletas") \
        .document(atleta_id) \
        .collection("jogos") \
        .document(jogo_id) \
        .update({
        "Minutos Jogados": minutos,
        "Gols Marcados": gols,
        "Assistências": assistencias,
        "Resultado": resultado,
        "status": "finalizado",
        "finalizado_em": firestore.SERVER_TIMESTAMP
    })


# ======================================================
# 📌 TREINOS
# ======================================================
def carregar_treinos_firestore(user_uid: str, atleta_id: str):
    docs = (
        db.collection("users")
        .document(user_uid)
        .collection("atletas")
        .document(atleta_id)
        .collection("treinos")
        .stream()
    )

    treinos = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        treinos.append(data)

    return treinos


def salvar_treino_firestore(user_uid: str, atleta_id: str, treino: dict):
    db.collection("users") \
        .document(user_uid) \
        .collection("atletas") \
        .document(atleta_id) \
        .collection("treinos") \
        .add(treino)

# ======================================================
# 📌 SONO
# ======================================================
def carregar_sono_firestore(user_uid: str, atleta_id: str):
    docs = (
        db.collection("users")
        .document(user_uid)
        .collection("atletas")
        .document(atleta_id)
        .collection("sono")
        .stream()
    )

    registros = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        registros.append(data)

    return registros

def salvar_sono_firestore(user_uid: str, atleta_id: str, sono: dict):
    db.collection("users") \
        .document(user_uid) \
        .collection("atletas") \
        .document(atleta_id) \
        .collection("sono") \
        .add(sono)


# ======================================================
# 📌 SAÚDE
# ======================================================
def carregar_saude_firestore(user_uid: str, atleta_id: str):
    docs = (
        db.collection("users")
        .document(user_uid)
        .collection("atletas")
        .document(atleta_id)
        .collection("saude")
        .stream()
    )

    registros = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        registros.append(data)

    return registros


def salvar_saude_firestore(user_uid: str, atleta_id: str, saude: dict):
    db.collection("users") \
        .document(user_uid) \
        .collection("atletas") \
        .document(atleta_id) \
        .collection("saude") \
        .add(saude)

