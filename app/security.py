import secrets
import string

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ohne verwechselbare Zeichen (0/O, 1/l/I) — wird laut vorgelesen/abgetippt
_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")


def generiere_passwort(laenge: int = 8) -> str:
    """Kurzes, aber zufälliges Start-Passwort für neu angelegte Mitarbeiter."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(laenge))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
