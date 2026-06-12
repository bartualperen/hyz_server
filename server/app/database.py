from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        # SQLite dosyasının klasörünü garantiye al
        if ":///" in url:
            db_path = url.split(":///", 1)[1]
            if db_path and db_path not in (":memory:",):
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Modeller metadata'ya kayıtlı olsun diye import edilir.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
