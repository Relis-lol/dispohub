from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.models import User, Role
from app.security import verify_password, hash_password
from app.services.rate_limit import gesperrt_fuer, fehlversuch_merken, erfolg_zuruecksetzen
from app.templating import templates

router = APIRouter()


def _home_for(user: User) -> str:
    if user.role == Role.fahrer:
        return "/chat"
    if user.role == Role.it:
        return "/it"
    return "/"


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unbekannt"
    sperre = gesperrt_fuer(ip, email)
    if sperre:
        minuten = max(1, sperre // 60)
        return templates.TemplateResponse(
            "login.html",
            {"request": request,
             "error": f"Zu viele Fehlversuche. Bitte in ca. {minuten} Minute(n) erneut versuchen."},
            status_code=429,
        )

    user = (db.query(User).filter(User.email == email.strip().lower(),
                                  User.geloescht_am.is_(None)).first())
    if not user or not verify_password(password, user.password_hash):
        fehlversuch_merken(ip, email)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "E-Mail oder Passwort ist falsch."},
            status_code=401,
        )
    erfolg_zuruecksetzen(ip, email)
    request.session["user_id"] = user.id
    if user.passwort_aendern_erforderlich:
        return RedirectResponse("/passwort?pflicht=1", status_code=303)
    return RedirectResponse(_home_for(user), status_code=303)


@router.post("/logout")
@router.get("/logout")
def logout(request: Request):
    """CSRF-Sonderfall (dokumentiert, siehe app/services/csrf.py):
    /logout wird bewusst über einen einfachen <a href> (GET) aufgerufen und
    trägt daher kein CSRF-Token. Das ist sicher, weil (1) same_site="lax" beim
    Session-Cookie einen von einer fremden Seite ausgelösten Request ohnehin
    ohne das Cookie ankommen lässt — ein Angreifer kann also gar nicht als der
    Nutzer erscheinen — und (2) der einzige Effekt ein Zurücksetzen der
    EIGENEN Session ist (kein Zugriff auf oder Änderung von Daten anderer
    Nutzer). Die POST-Variante bleibt für zukünftige Formulare erhalten und
    wird wie jedes andere Formular durch die CSRFMiddleware geprüft, sobald
    es tatsächlich Formulardaten enthält."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/passwort", response_class=HTMLResponse)
def passwort_form(request: Request, user: User = Depends(require_user), pflicht: int = 0):
    return templates.TemplateResponse(
        "account/passwort.html",
        {"request": request, "user": user, "active": "passwort", "error_key": None,
         "pflicht": bool(pflicht)},
    )


@router.post("/passwort")
def passwort_aendern(request: Request, user: User = Depends(require_user),
                     db: Session = Depends(get_db),
                     altes_passwort: str = Form(...), neues_passwort: str = Form(...),
                     neues_passwort_wiederholen: str = Form(...)):
    def fehler(schluessel: str):
        return templates.TemplateResponse(
            "account/passwort.html",
            {"request": request, "user": user, "active": "passwort", "error_key": schluessel,
             "pflicht": user.passwort_aendern_erforderlich},
            status_code=400,
        )

    if not verify_password(altes_passwort, user.password_hash):
        return fehler("password_page.err_wrong_current")
    if len(neues_passwort) < 6:
        return fehler("password_page.err_too_short")
    if neues_passwort != neues_passwort_wiederholen:
        return fehler("password_page.err_mismatch")

    user.password_hash = hash_password(neues_passwort)
    user.passwort_aendern_erforderlich = False
    db.commit()
    return RedirectResponse(_home_for(user), status_code=303)
