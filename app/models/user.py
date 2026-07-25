import enum
from datetime import date, datetime, time

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Date, DateTime, Time, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Erreichbarkeit(str, enum.Enum):
    gruen = "gruen"        # jederzeit anrufbar
    rot = "rot"            # bitte nicht anrufen (Fahrer bekommt Rückfrage)
    zeitplan = "zeitplan"  # nur innerhalb der eingestellten Uhrzeiten grün


class Role(str, enum.Enum):
    admin = "admin"
    geschaeftsfuehrung = "geschaeftsfuehrung"
    buero = "buero"
    it = "it"
    fahrer = "fahrer"


class UserStatus(str, enum.Enum):
    aktiv = "aktiv"
    abwesend = "abwesend"
    inaktiv = "inaktiv"


ROLE_LABELS = {
    Role.admin: "Administrator",
    Role.geschaeftsfuehrung: "Geschäftsführung",
    Role.buero: "Büroleitung",
    Role.it: "IT-Zugriff",
    Role.fahrer: "Fahrer",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.fahrer)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.aktiv)
    geburtstag: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Nur für GF/Büro relevant: Anrufe von Fahrern nur im echten Notfall erwünscht
    nur_notfall_anrufen: Mapped[bool] = mapped_column(Boolean, default=False)
    # Nach dem Anlegen mit Zufalls-Passwort gesetzt, erzwingt Passwort ändern beim nächsten Login
    passwort_aendern_erforderlich: Mapped[bool] = mapped_column(Boolean, default=False)

    # Anrufbereitschaft für Fahrer: grün/rot oder Zeitplan (DND außerhalb der Zeiten)
    erreichbarkeit: Mapped[Erreichbarkeit] = mapped_column(
        SAEnum(Erreichbarkeit), default=Erreichbarkeit.gruen
    )
    erreichbar_von: Mapped[time | None] = mapped_column(Time, nullable=True)
    erreichbar_bis: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Personalakte
    foto_pfad: Mapped[str | None] = mapped_column(String(400), nullable=True)
    urlaubstage_kontingent: Mapped[int] = mapped_column(default=24)
    fahrerkarte_ablauf: Mapped[date | None] = mapped_column(Date, nullable=True)
    adr_karte_ablauf: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Aktuell zugeordnetes Fahrzeug (nur für Fahrer relevant)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    vehicle: Mapped["Vehicle | None"] = relationship(  # noqa: F821
        back_populates="driver", foreign_keys=[vehicle_id]
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Papierkorb: gesetzt = gelöscht, nach 30 Tagen endgültige Entfernung
    geloescht_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role.value)

    @property
    def ist_erreichbar(self) -> bool:
        """Ampel für den Fahrer: darf ich gerade anrufen?"""
        if self.erreichbarkeit == Erreichbarkeit.rot:
            return False
        if self.erreichbarkeit == Erreichbarkeit.zeitplan:
            if not self.erreichbar_von or not self.erreichbar_bis:
                return True
            jetzt = datetime.now().time()
            von, bis = self.erreichbar_von, self.erreichbar_bis
            if von <= bis:
                return von <= jetzt <= bis
            # Fenster über Mitternacht (z.B. 20:00-06:00)
            return jetzt >= von or jetzt <= bis
        return True
