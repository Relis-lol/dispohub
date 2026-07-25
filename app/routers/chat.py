from datetime import datetime, timedelta

from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, WebSocket,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.deps import require_user
from app.models import (
    User, Role, Vehicle, VehicleStatus,
    ChatThread, ChatMembership, ChatMessage, ThreadArt,
    DamageReport, DamageStatus, Priority, Document,
)
from app.services.uploads import save_upload
from app.services.ws import manager
from app.services.chat_service import unread_count, unread_for_thread
from app.templating import templates, to_local

router = APIRouter()

# Eigene Nachrichten/Bilder sind für kurze Zeit rückgängig machbar (Tippfehler etc.)
LOESCHEN_FENSTER = timedelta(minutes=2)

# Diese Gruppen sind reine Durchsagen von GF/Büro - Fahrer lesen mit, schreiben aber nicht
# hinein (verhindert Fahrer-Fahrer-Diskussionen im großen Verteiler).
BROADCAST_NUR_GRUPPEN = {"Alle", "Alle Fahrer"}


def _kann_senden(thread: ChatThread, user: User) -> bool:
    if thread.art == ThreadArt.gruppe and thread.name in BROADCAST_NUR_GRUPPEN and user.role == Role.fahrer:
        return False
    return True


# --- Hilfsfunktionen --------------------------------------------------------
def _threads_for(db: Session, user: User) -> list[ChatThread]:
    thread_ids = db.scalars(
        select(ChatMembership.thread_id).where(ChatMembership.user_id == user.id)
    ).all()
    if not thread_ids:
        return []
    threads = db.query(ChatThread).filter(ChatThread.id.in_(thread_ids)).all()
    # nach letzter Nachricht sortieren (neueste zuerst)
    threads.sort(key=lambda t: (t.messages[-1].id if t.messages else 0), reverse=True)
    return threads


def _membership(db: Session, thread_id: int, user: User) -> ChatMembership | None:
    return (
        db.query(ChatMembership)
        .filter(ChatMembership.thread_id == thread_id, ChatMembership.user_id == user.id)
        .first()
    )


def _is_mobile_driver(user: User) -> bool:
    return user.role == Role.fahrer


# --- Views ------------------------------------------------------------------
@router.get("/chat", response_class=HTMLResponse)
def chat_index(request: Request, user: User = Depends(require_user),
               db: Session = Depends(get_db)):
    threads = _threads_for(db, user)
    unread = {t.id: unread_for_thread(db, _membership(db, t.id, user), user) for t in threads}
    # Ersten Thread als aktiven öffnen (Desktop)
    active_thread = threads[0] if threads else None
    ctx = {
        "request": request, "user": user, "active": "chat",
        "threads": threads, "unread": unread, "t": active_thread,
        "messages": active_thread.messages if active_thread else [],
        "kann_senden": _kann_senden(active_thread, user) if active_thread else True,
    }
    if active_thread:
        _mark_read(db, active_thread, user)
    template = "chat/mobile.html" if _is_mobile_driver(user) else "chat/index.html"
    return templates.TemplateResponse(template, ctx)


@router.get("/chat/{thread_id}", response_class=HTMLResponse)
def chat_thread(thread_id: int, request: Request, user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    m = _membership(db, thread_id, user)
    if not m:
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Unterhaltung")
    thread = db.get(ChatThread, thread_id)
    threads = _threads_for(db, user)
    unread = {t.id: unread_for_thread(db, _membership(db, t.id, user), user) for t in threads}
    _mark_read(db, thread, user)
    ctx = {
        "request": request, "user": user, "active": "chat",
        "threads": threads, "unread": unread, "t": thread, "messages": thread.messages,
        "kann_senden": _kann_senden(thread, user),
    }
    template = "chat/mobile_thread.html" if _is_mobile_driver(user) else "chat/index.html"
    return templates.TemplateResponse(template, ctx)


def _mark_read(db: Session, thread: ChatThread, user: User) -> None:
    m = _membership(db, thread.id, user)
    if m and thread.messages:
        newest = thread.messages[-1].id
        if m.last_read_message_id != newest:
            m.last_read_message_id = newest
            db.commit()


@router.post("/chat/{thread_id}/senden")
async def senden(thread_id: int, request: Request, user: User = Depends(require_user),
                 db: Session = Depends(get_db),
                 text: str = Form(""), bild: UploadFile | None = File(default=None),
                 audio: UploadFile | None = File(default=None)):
    m = _membership(db, thread_id, user)
    if not m:
        raise HTTPException(status_code=403, detail="Kein Zugriff")
    if not _kann_senden(m.thread, user):
        raise HTTPException(status_code=403, detail="In dieser Gruppe können nur GF/Büro schreiben")

    doc = save_upload(bild) if bild else None
    if not doc and audio:
        doc = save_upload(audio, audio=True)
    if not text.strip() and not doc:
        # nichts zu senden
        return Response(status_code=204)

    msg = ChatMessage(thread_id=thread_id, sender_id=user.id, text=(text.strip() or None))
    if doc:
        db.add(doc)
        db.flush()
        msg.document_id = doc.id
    db.add(msg)
    # Absender hat die eigene Nachricht sofort gelesen
    m.last_read_message_id = None  # wird nach flush gesetzt
    db.flush()
    m.last_read_message_id = msg.id
    db.commit()
    db.refresh(msg)

    payload = {
        "type": "message",
        "id": msg.id,
        "thread_id": thread_id,
        "sender_id": user.id,
        "sender_name": user.name,
        "text": msg.text or "",
        "image": doc.pfad if doc and doc.typ != "audio" else None,
        "audio": doc.pfad if doc and doc.typ == "audio" else None,
        "time": to_local(msg.created_at).strftime("%H:%M") if msg.created_at else datetime.now().strftime("%H:%M"),
    }
    await manager.broadcast(thread_id, payload)

    if request.headers.get("X-WS") == "1":
        return Response(status_code=204)
    return RedirectResponse(f"/chat/{thread_id}", status_code=303)


@router.post("/chat/nachricht/{message_id}/loeschen")
async def nachricht_loeschen(message_id: int, user: User = Depends(require_user),
                             db: Session = Depends(get_db)):
    msg = db.get(ChatMessage, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")
    if msg.sender_id != user.id:
        raise HTTPException(status_code=403, detail="Nur eigene Nachrichten löschbar")
    # created_at ist UTC-naiv (SQLite CURRENT_TIMESTAMP) -> gegen UTC-"jetzt" vergleichen,
    # sonst verfälscht die lokale Zeitzone das Zeitfenster.
    if datetime.utcnow() - msg.created_at > LOESCHEN_FENSTER:
        raise HTTPException(status_code=403, detail="Löschen ist nur innerhalb von 2 Minuten möglich")

    msg.geloescht = True
    msg.text = None
    msg.document_id = None
    db.commit()

    await manager.broadcast(msg.thread_id, {"type": "delete", "id": msg.id})
    return Response(status_code=204)


# --- WebSocket --------------------------------------------------------------
def _herkunft_erlaubt(websocket: WebSocket) -> bool:
    """Cross-Site-WebSocket-Schutz: die Origin-Prüfung, die same_site=lax bei
    normalen Formularen übernimmt, greift bei WebSocket-Handshakes nicht
    automatisch (Browser blocken Cross-Origin-WS nicht von sich aus) — deshalb
    hier explizit gegen den Host der Anfrage prüfen."""
    origin = websocket.headers.get("origin")
    if not origin:
        return True  # z.B. native Apps/Tools ohne Origin-Header
    host = websocket.headers.get("host", "")
    return origin.endswith(f"://{host}")


@router.websocket("/ws/chat/{thread_id}")
async def ws_chat(websocket: WebSocket, thread_id: int):
    if not _herkunft_erlaubt(websocket):
        await websocket.close(code=1008)
        return
    user_id = websocket.session.get("user_id") if hasattr(websocket, "session") else None
    if not user_id:
        await websocket.close(code=1008)
        return
    # Mitgliedschaft prüfen
    db = SessionLocal()
    try:
        is_member = (
            db.query(ChatMembership)
            .filter(ChatMembership.thread_id == thread_id, ChatMembership.user_id == user_id)
            .first()
            is not None
        )
    finally:
        db.close()
    if not is_member:
        await websocket.close(code=1008)
        return

    await manager.connect(thread_id, websocket)
    try:
        while True:
            # Wir empfangen nur zum Verbindung-Halten; Senden läuft über POST.
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        await manager.disconnect(thread_id, websocket)


# --- Bild aus Chat übernehmen ----------------------------------------------
@router.post("/chat/nachricht/{message_id}/als-schaden")
def bild_als_schaden(message_id: int, request: Request, user: User = Depends(require_user),
                     db: Session = Depends(get_db), vehicle_id: str = Form("")):
    msg = db.get(ChatMessage, message_id)
    if not msg or not msg.document_id:
        raise HTTPException(status_code=404, detail="Kein Bild an dieser Nachricht")
    if not _membership(db, msg.thread_id, user):
        raise HTTPException(status_code=403, detail="Kein Zugriff")

    # Fahrzeug bestimmen: explizit gewählt, sonst Fahrzeug des Absenders
    vid = int(vehicle_id) if vehicle_id.strip() else (msg.sender.vehicle_id if msg.sender else None)
    if not vid:
        raise HTTPException(status_code=400, detail="Kein Fahrzeug zuzuordnen")

    doc = db.get(Document, msg.document_id)
    report = DamageReport(
        vehicle_id=vid, reporter_id=msg.sender_id,
        beschreibung=(msg.text or "Aus Chat übernommen"),
        prioritaet=Priority.normal, status=DamageStatus.gemeldet,
    )
    # Bild kopieren (neues Document, damit Chat-Bild erhalten bleibt)
    report.documents.append(Document(pfad=doc.pfad, typ="foto", dateiname=doc.dateiname))
    db.add(report)
    db.commit()
    return RedirectResponse(f"/schaeden/{report.id}", status_code=303)


@router.post("/chat/nachricht/{message_id}/an-fahrzeug/{vehicle_id}")
def bild_an_fahrzeug(message_id: int, vehicle_id: int, user: User = Depends(require_user),
                     db: Session = Depends(get_db)):
    msg = db.get(ChatMessage, message_id)
    if not msg or not msg.document_id:
        raise HTTPException(status_code=404, detail="Kein Bild an dieser Nachricht")
    if not _membership(db, msg.thread_id, user):
        raise HTTPException(status_code=403, detail="Kein Zugriff")
    doc = db.get(Document, msg.document_id)
    db.add(Document(pfad=doc.pfad, typ="foto", dateiname=doc.dateiname, vehicle_id=vehicle_id))
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)
