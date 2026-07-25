FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrationen vor dem Start anwenden, statt sich nur auf create_all() zu verlassen
# (das läuft weiterhin als Dev-Sicherheitsnetz mit, siehe app/main.py).
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
