from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Client, Dataset, EvalSession


def resolve_session(db: Session, client: Client) -> tuple[EvalSession | None, Dataset | None]:
    """Client'ın aktif oturumunu çöz. Aktif oturum atanmamışsa en yeni 'running'
    oturuma düşer ve onu client'a sabitler."""
    session = None
    if client.active_session_id:
        session = db.get(EvalSession, client.active_session_id)

    if session is None:
        session = db.scalar(
            select(EvalSession)
            .where(EvalSession.status == "running")
            .order_by(EvalSession.created_at.desc())
        )
        if session is not None and client.active_session_id != session.id:
            client.active_session_id = session.id
            db.commit()

    if session is None:
        return None, None

    dataset = db.get(Dataset, session.dataset_id)
    return session, dataset
