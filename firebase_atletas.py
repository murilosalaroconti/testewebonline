from firebase_admin import firestore
from datetime import datetime
from firebase_db import db



def listar_atletas(user_uid):
    atletas_ref = db.collection("users").document(user_uid).collection("atletas")
    docs = atletas_ref.stream()

    atletas = []
    for doc in docs:
        data = doc.to_dict()
        atletas.append({
            "id": doc.id,
            "nome": data.get("nome", "Sem nome")
        })

    return atletas

def criar_atleta(user_uid, nome):
    atletas_ref = db.collection("users").document(user_uid).collection("atletas")

    doc_ref = atletas_ref.document()
    doc_ref.set({
        "nome": nome,
        "criado_em": firestore.SERVER_TIMESTAMP
    })

    return doc_ref.id
