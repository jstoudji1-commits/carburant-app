"""Models SQLAlchemy pour OptiPlein."""
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    JSON,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import os

Base = declarative_base()


class User(Base):
    """Modèle utilisateur."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(160), unique=True, index=True, nullable=False)
    password_salt = Column(String(32), nullable=False)
    password_hash = Column(String(64), nullable=False)
    password_iterations = Column(Integer, default=260000)
    email_verified = Column(Boolean, default=False)
    email_verification_hash = Column(String(64), nullable=True)
    email_verification_expires_at = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Données utilisateur (JSON)
    favoris = Column(JSON, default=[])
    vehicules = Column(JSON, default=[])
    vehicule_actif = Column(String(255), default="")
    plan = Column(String(20), default="free")  # 'free' ou 'premium'
    historique_economies = Column(JSON, default=[])
    lieux_trajet = Column(JSON, default={})
    rayon_stations = Column(Integer, default=25)

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_created_at', 'created_at'),
    )


class Station(Base):
    """Modèle station carburant."""
    __tablename__ = "stations"

    id = Column(String(32), primary_key=True, index=True)
    enseigne = Column(String(120), index=True)
    adresse = Column(String(180))
    cp = Column(String(12), index=True)
    ville = Column(String(90), index=True)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    
    # Prix carburants
    gazole = Column(String(10), default="")
    e10 = Column(String(10), default="")
    sp98 = Column(String(10), default="")
    
    # Tendances
    tendance_gazole = Column(String(20), default="")
    tendance_e10 = Column(String(20), default="")
    tendance_sp98 = Column(String(20), default="")
    
    # Tendances demain
    tendance_demain_gazole = Column(String(20), default="")
    tendance_demain_e10 = Column(String(20), default="")
    tendance_demain_sp98 = Column(String(20), default="")
    
    # Confiance sur tendance demain
    confiance_demain_gazole = Column(String(20), default="")
    confiance_demain_e10 = Column(String(20), default="")
    confiance_demain_sp98 = Column(String(20), default="")
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_station_location', 'latitude', 'longitude'),
        Index('idx_station_ville_cp', 'ville', 'cp'),
    )


class StationEnrichment(Base):
    """Enrichissement et corrections de stations."""
    __tablename__ = "station_enrichments"

    id = Column(Integer, primary_key=True)
    station_id = Column(String(32), index=True, nullable=False)
    
    # Champs corrigés
    enseigne = Column(String(120), nullable=True)
    adresse = Column(String(180), nullable=True)
    cp = Column(String(12), nullable=True)
    ville = Column(String(90), nullable=True)
    latitude_corrigee = Column(Float, nullable=True)
    longitude_corrigee = Column(Float, nullable=True)
    
    # Métadonnées
    signature = Column(String(255), nullable=True)
    source_enseigne = Column(String(120), default="")
    source_correction = Column(String(120), default="")
    forcer_correction = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_enrichment_station_id', 'station_id'),
    )


class Tester(Base):
    """Testeur inscrit via landing page."""
    __tablename__ = "testers"

    id = Column(Integer, primary_key=True)
    email = Column(String(160), unique=True, index=True, nullable=False)
    source = Column(String(80), default="landing")
    ip_address = Column(String(45), nullable=True)  # IPv4 ou IPv6
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_tester_email_created', 'email', 'created_at'),
    )


class Report(Base):
    """Signalement de problème utilisateur."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    station_id = Column(String(32), nullable=True, index=True)
    email = Column(String(160), nullable=True)
    page = Column(String(300), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String(20), default="open")  # open, acknowledged, resolved
    
    __table_args__ = (
        Index('idx_report_created_status', 'created_at', 'status'),
    )


class DataVersion(Base):
    """Versioning des données de stations."""
    __tablename__ = "data_versions"

    id = Column(Integer, primary_key=True)
    version = Column(String(50), unique=True, index=True)
    stations_count = Column(Integer)
    last_update = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_version_created', 'created_at'),
    )


def get_database_url():
    """Obtient l'URL de la base de données depuis les variables d'env."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    # Fallback sur SQLite pour développement local
    return os.getenv("DATABASE_URL_DEV", "sqlite:///./optiplein.db")


def create_db_engine():
    """Crée le moteur SQLAlchemy."""
    url = get_database_url()
    
    # Options spécifiques pour PostgreSQL
    if url.startswith("postgresql://") or url.startswith("postgresql+psycopg2://"):
        engine = create_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Vérifie la connexion avant usage
            echo=False,
        )
    else:
        # SQLite
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    
    return engine


def create_session():
    """Crée une session SQLAlchemy."""
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_db():
    """Initialise la base de données."""
    engine = create_db_engine()
    Base.metadata.create_all(bind=engine)
