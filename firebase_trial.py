from firebase_admin import firestore
from datetime import datetime
from firebase_db import db


def get_info_trial(user_uid):
    doc = db.collection("users").document(user_uid).get()
    if not doc.exists:
        return None

    data = doc.to_dict()

    if not data.get("teste_gratis"):
        return None

    expira_em = data.get("expira_em")
    if not expira_em:
        return None

    dias_restantes = (expira_em.replace(tzinfo=None) - datetime.now()).days

    return {
        "ativo": dias_restantes >= 0,
        "dias_restantes": max(dias_restantes, 0)
    }

def get_plano_usuario(user_uid):
    doc = db.collection("users").document(user_uid).get()

    if not doc.exists:
        return {
            "plano": "free",
            "plano_ativo": False
        }

    data = doc.to_dict()

    return {
        "plano": data.get("plano", "free"),
        "plano_ativo": data.get("plano_ativo", False)
    }

