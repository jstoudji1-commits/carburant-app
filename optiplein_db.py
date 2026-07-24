import os
from contextlib import contextmanager


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

try:
    from sqlalchemy import Boolean, Column, String, Text, create_engine
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm import Session, declarative_base
except ImportError:  # pragma: no cover - local fallback without DB deps
    Boolean = Column = String = Text = create_engine = JSONB = Session = None
    declarative_base = None


def _normaliser_database_url(url):

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def _texte_nullable(valeur):

    if valeur in (None, ""):
        return None

    return str(valeur)


Base = declarative_base() if declarative_base else None
_engine = None
_initialise = False


def base_donnees_active():

    return bool(DATABASE_URL and Base and create_engine)


def libelle_stockage():

    return "postgresql" if base_donnees_active() else "json"


if Base:

    class CompteUtilisateur(Base):
        __tablename__ = "user_accounts"

        email = Column(String(160), primary_key=True)
        password = Column(JSONB, nullable=False, default=dict)
        data = Column(JSONB, nullable=False, default=dict)
        email_verified = Column(Boolean, nullable=False, default=True)
        email_verification_hash = Column(String(128), nullable=True)
        email_verification_expires_at = Column(String(40), nullable=True)
        password_reset_hash = Column(String(128), nullable=True)
        password_reset_expires_at = Column(String(40), nullable=True)
        created_at = Column(String(40), nullable=False)
        updated_at = Column(String(40), nullable=False)

    class TesteurLanding(Base):
        __tablename__ = "landing_testers"

        email = Column(String(160), primary_key=True)
        source = Column(String(80), nullable=False, default="landing")
        created_at = Column(String(40), nullable=False)
        updated_at = Column(String(40), nullable=False)
        ip = Column(String(80), nullable=False, default="")

    class CorrectionStation(Base):
        __tablename__ = "station_overrides"

        station_id = Column(String(80), primary_key=True)
        payload = Column(JSONB, nullable=False, default=dict)
        source = Column(String(80), nullable=False, default="admin-overrides")
        updated_at = Column(String(40), nullable=False)

    class DonneeApplication(Base):
        __tablename__ = "app_kv_store"

        key = Column(String(120), primary_key=True)
        value = Column(JSONB, nullable=False, default=dict)
        updated_at = Column(String(40), nullable=False)


def moteur():

    global _engine

    if not base_donnees_active():
        return None

    if _engine is None:
        _engine = create_engine(
            _normaliser_database_url(DATABASE_URL),
            pool_pre_ping=True,
            future=True,
        )

    return _engine


def initialiser_base():

    global _initialise

    if _initialise or not base_donnees_active():
        return

    Base.metadata.create_all(moteur())
    _initialise = True


@contextmanager
def session_base():

    initialiser_base()
    session = Session(moteur())

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def charger_comptes():

    if not base_donnees_active():
        return None

    with session_base() as session:
        comptes = {"users": {}}

        for ligne in session.query(CompteUtilisateur).all():
            utilisateur = {
                "email": ligne.email,
                "password": ligne.password or {},
                "created_at": ligne.created_at,
                "updated_at": ligne.updated_at,
                "email_verified": ligne.email_verified,
                "data": ligne.data or {},
            }

            if ligne.email_verification_hash:
                utilisateur["email_verification_hash"] = (
                    ligne.email_verification_hash
                )

            if ligne.email_verification_expires_at:
                utilisateur["email_verification_expires_at"] = (
                    ligne.email_verification_expires_at
                )

            if ligne.password_reset_hash:
                utilisateur["password_reset_hash"] = ligne.password_reset_hash

            if ligne.password_reset_expires_at:
                utilisateur["password_reset_expires_at"] = (
                    ligne.password_reset_expires_at
                )

            comptes["users"][ligne.email] = utilisateur

        return comptes


def enregistrer_comptes(donnees):

    if not base_donnees_active():
        return False

    utilisateurs = donnees.get("users", {}) if isinstance(donnees, dict) else {}

    with session_base() as session:
        emails = set(utilisateurs)

        for email, utilisateur in utilisateurs.items():
            ligne = session.get(CompteUtilisateur, email)

            if not ligne:
                ligne = CompteUtilisateur(email=email)
                session.add(ligne)

            ligne.password = utilisateur.get("password", {})
            ligne.data = utilisateur.get("data", {})
            ligne.email_verified = bool(
                utilisateur.get("email_verified", True)
            )
            ligne.email_verification_hash = utilisateur.get(
                "email_verification_hash"
            )
            ligne.email_verification_expires_at = _texte_nullable(
                utilisateur.get("email_verification_expires_at")
            )
            ligne.password_reset_hash = utilisateur.get("password_reset_hash")
            ligne.password_reset_expires_at = _texte_nullable(
                utilisateur.get("password_reset_expires_at")
            )
            ligne.created_at = utilisateur.get("created_at", "")
            ligne.updated_at = utilisateur.get("updated_at", "")

        for ligne in session.query(CompteUtilisateur).all():
            if ligne.email not in emails:
                session.delete(ligne)

    return True


def charger_testeurs():

    if not base_donnees_active():
        return None

    with session_base() as session:
        return {
            "testeurs": [
                {
                    "email": ligne.email,
                    "source": ligne.source,
                    "created_at": ligne.created_at,
                    "updated_at": ligne.updated_at,
                    "ip": ligne.ip,
                }
                for ligne in session.query(TesteurLanding).all()
            ]
        }


def enregistrer_testeurs(donnees):

    if not base_donnees_active():
        return False

    testeurs = (
        donnees.get("testeurs", [])
        if isinstance(donnees, dict)
        else []
    )

    with session_base() as session:
        emails = set()

        for testeur in testeurs:
            email = testeur.get("email", "")
            if not email:
                continue

            emails.add(email)
            ligne = session.get(TesteurLanding, email)

            if not ligne:
                ligne = TesteurLanding(email=email)
                session.add(ligne)

            ligne.source = testeur.get("source", "landing")
            ligne.created_at = testeur.get("created_at", "")
            ligne.updated_at = testeur.get("updated_at", "")
            ligne.ip = testeur.get("ip", "")

        for ligne in session.query(TesteurLanding).all():
            if ligne.email not in emails:
                session.delete(ligne)

    return True


def charger_corrections_stations():

    if not base_donnees_active():
        return None

    with session_base() as session:
        return {
            "source": "postgresql",
            "stations": {
                ligne.station_id: ligne.payload or {}
                for ligne in session.query(CorrectionStation).all()
            },
        }


def enregistrer_correction_station(station_id, correction):

    if not base_donnees_active():
        return False

    with session_base() as session:
        ligne = session.get(CorrectionStation, str(station_id))

        if not ligne:
            ligne = CorrectionStation(station_id=str(station_id))
            session.add(ligne)

        ligne.payload = dict(correction or {})
        ligne.source = ligne.payload.get("source_correction") or "admin-overrides"
        ligne.updated_at = ligne.payload.get("updated_at", "")

    return True
