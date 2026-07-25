from sqlalchemy import String, Boolean

from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AreaPermission(Base):
    """Von der Geschäftsführung einstellbar: darf die Rolle 'Büro' diesen Bereich sehen?

    Admin und Geschäftsführung haben immer vollen Zugriff, unabhängig von dieser Tabelle.
    Fehlt ein Eintrag für einen Bereich, gilt er als erlaubt (bestehendes Verhalten).
    """

    __tablename__ = "area_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    bereich: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    buero_erlaubt: Mapped[bool] = mapped_column(Boolean, default=True)
