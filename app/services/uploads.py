"""Gemeinsames Datei-Upload-Handling (Schaden-Fotos, Chat-Bilder, Belege)."""
import os
import uuid

from fastapi import UploadFile

from app.models import Document, Receipt

UPLOAD_DIR = os.path.join("app", "static", "uploads")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# Für Dokumente (z.B. Arbeitsverträge) zusätzlich PDF zulassen.
ALLOWED_DOC_EXT = ALLOWED_EXT | {".pdf"}
# Sprachnachrichten aus dem Browser (MediaRecorder) bzw. vom Handy.
ALLOWED_AUDIO_EXT = {".webm", ".ogg", ".m4a", ".mp3", ".wav"}


def save_upload(file: UploadFile | None, *, dokumente: bool = False,
                audio: bool = False) -> Document | None:
    """Speichert ein Bild (dokumente=True: auch PDF, audio=True: Audiodateien)
    und liefert ein (noch nicht committetes) Document zurück."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    erlaubt = ALLOWED_AUDIO_EXT if audio else (ALLOWED_DOC_EXT if dokumente else ALLOWED_EXT)
    if ext not in erlaubt:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, name)
    with open(dest, "wb") as fh:
        fh.write(file.file.read())
    if audio:
        typ = "audio"
    elif ext == ".pdf":
        typ = "dokument"
    else:
        typ = "foto"
    return Document(pfad=f"/static/uploads/{name}", typ=typ, dateiname=file.filename)


def save_receipt(file: UploadFile | None, hochgeladen_von_id: int,
                 notiz: str | None = None) -> Receipt | None:
    """Speichert einen rohen Beleg für den Steuerberater-Filedrop (Bild oder PDF)."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXT:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, name)
    with open(dest, "wb") as fh:
        fh.write(file.file.read())
    return Receipt(pfad=f"/static/uploads/{name}", dateiname=file.filename,
                    notiz=notiz, hochgeladen_von_id=hochgeladen_von_id)
