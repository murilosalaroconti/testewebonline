from firebase_admin import auth

def login_firebase(email: str, password: str):
    """
    MVP: valida se o usuário existe no Firebase Auth.
    A senha NÃO é validada pelo Admin SDK.
    """
    try:
        user = auth.get_user_by_email(email)
        return {
            "uid": user.uid,
            "email": user.email
        }
    except Exception:
        return None


def criar_usuario_firebase(email: str, password: str):
    """
    Cria um novo usuário no Firebase Authentication
    """
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
        return {
            "uid": user.uid,
            "email": user.email
        }
    except Exception:
        return None
