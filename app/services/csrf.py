"""CSRF-Schutz für alle POST-Formulare.

Statt jedes der ~50 Formulare einzeln um ein verstecktes Feld zu ergänzen,
macht diese Middleware zwei Dinge automatisch:
1. Fügt jedem ausgehenden HTML-Formular (<form ...method="post"...>) ein
   verstecktes csrf_token-Feld mit dem Token der aktuellen Session ein.
2. Prüft bei eingehenden POST-Requests mit Formulardaten, ob das Token zum
   Session-Token passt — sonst 403.

Ergänzt den bestehenden Schutz durch same_site="lax" beim Session-Cookie
(der schon die meisten Cross-Site-POSTs verhindert); das Token schützt
zusätzlich gegen ältere Browser und andere Sonderfälle.
"""
import re
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

FORM_TAG_RE = re.compile(
    r'(<form\b[^>]*\bmethod=["\']post["\'][^>]*>)', re.IGNORECASE
)


def _token_fuer(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        request.session["csrf_token"] = token
    return token


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_type = request.headers.get("content-type", "")
        ist_formular = "application/x-www-form-urlencoded" in content_type or \
            "multipart/form-data" in content_type

        if request.method == "POST" and ist_formular and settings.csrf_protection_enabled:
            # Wichtig: erst .body() aufrufen, damit Starlettes BaseHTTPMiddleware
            # den Request-Body cached und an den eigentlichen Handler
            # weiterreicht. .form() liest sonst intern per .stream() — das
            # würde den Body für den nachgelagerten Handler leeren (der bekäme
            # dann leere Formulardaten -> 422).
            await request.body()
            form = await request.form()
            gesendet = form.get("csrf_token")
            erwartet = request.session.get("csrf_token")
            if not erwartet or gesendet != erwartet:
                # HTTPException hier zu werfen würde NICHT von den regulären
                # FastAPI-Exception-Handlern abgefangen (diese Middleware liegt
                # außerhalb davon) — deshalb direkt die gestylte Fehlerseite rendern.
                from app.templating import templates
                return templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request, "icon": "🔄", "titel": "Sicherheitsprüfung fehlgeschlagen",
                        "text": "Das Formular ist abgelaufen oder wurde in einem anderen Tab/Fenster "
                                "geöffnet. Bitte Seite neu laden und erneut versuchen.",
                        "angemeldet_als": None, "rolle_label": None,
                    },
                    status_code=403,
                )

        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type and hasattr(response, "body_iterator"):
            body_bytes = b"".join([chunk async for chunk in response.body_iterator])
            html = body_bytes.decode("utf-8", errors="replace")
            if FORM_TAG_RE.search(html):
                token = _token_fuer(request)
                feld = f'<input type="hidden" name="csrf_token" value="{token}">'
                html = FORM_TAG_RE.sub(lambda m: m.group(1) + feld, html)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return Response(
                content=html.encode("utf-8"), status_code=response.status_code,
                headers=headers, media_type=response.media_type,
            )
        return response
