from firebase_admin import auth, firestore
from datetime import datetime, timedelta, timezone
import requests
from firebase_db import db

FIREBASE_API_KEY = "AIzaSyCo7u6bzRTkJQ8VUwtJ_aASMEt8d4VPTs0"

# ===============================
# LOGIN
# ===============================
def login_firebase(email: str, password: str):
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return None

        return {
            "uid": data["localId"],
            "email": data["email"]
        }

    except Exception:
        return None

def enviar_email_reset_senha(email: str) -> bool:
    """
    Envia email de redefinição de senha via Firebase Auth
    """
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
        f"?key={FIREBASE_API_KEY}"
    )

    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False



# ===============================
# CRIAR USUÁRIO
# ===============================
def criar_usuario_firebase(email: str, password: str):
    try:
        user = auth.create_user(email=email, password=password)
        return {
            "uid": user.uid,
            "email": user.email
        }
    except Exception:
        return None


# ===============================
# 🆓 TRIAL
# ===============================

DIAS_TESTE_GRATUITO = 2  # 7 / 15 / 30

def verificar_trial_ativo(user_uid: str) -> bool:
    doc = db.collection("users").document(user_uid).get()

    if not doc.exists:
        return False

    data = doc.to_dict()

    if not data.get("teste_gratis", False):
        return True  # futuro: plano pago

    expira_em = data.get("expira_em")

    if not expira_em:
        return False

    agora = datetime.now(timezone.utc)

    return agora <= expira_em
