from fastapi import Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Role


class RedirectToLogin(Exception):
    """Signalisiert dem Handler, dass zum Login umgeleitet werden soll."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    # Im Papierkorb = ausgesperrt, auch wenn die Session noch läuft
    if user and user.geloescht_am:
        return None
    return user


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        # Wird im Exception-Handler zu einem Redirect auf /login.
        raise RedirectToLogin()
    return user


def require_roles(*roles: Role):
    """Dependency-Factory: erlaubt nur bestimmte Rollen."""

    def checker(user: User = Depends(require_user)) -> User:
        if user.role not in roles and user.role != Role.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff")
        return user

    return checker


# Häufige Kombinationen
def require_office(user: User = Depends(require_user)) -> User:
    """Büro-/Leitungsbereiche: Admin, Geschäftsführung, Büro (nicht Fahrer, nicht IT)."""
    if user.role not in (Role.admin, Role.geschaeftsfuehrung, Role.buero):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff")
    return user


def require_gf_or_admin(user: User = Depends(require_user)) -> User:
    """Nur Geschäftsführung/Admin: z.B. Rechte-Einstellungen."""
    if user.role not in (Role.admin, Role.geschaeftsfuehrung):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff")
    return user


def require_it_or_admin(user: User = Depends(require_user)) -> User:
    """IT-Zugang: technische Bereiche, keine Finanzdaten."""
    if user.role not in (Role.admin, Role.it):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff")
    return user


def require_area(bereich: str):
    """Dependency-Factory: Admin/GF immer erlaubt, Büro je nach GF-Einstellung, sonst nie."""

    def checker(request: Request, user: User = Depends(require_user),
               db: Session = Depends(get_db)) -> User:
        from app.services.permissions import is_erlaubt
        if not is_erlaubt(db, user, bereich):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf diesen Bereich")
        return user

    return checker
