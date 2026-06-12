from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_client
from ..models import Client
from ..services.context import resolve_session

router = APIRouter()


@router.get("/session/")
def get_session(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """İstemcinin ana akışı kullanmıyor ama protokol bütünlüğü için sağlanır."""
    session, dataset = resolve_session(db, client)
    if session is None:
        return JSONResponse(status_code=409, content={"detail": "No active session."})
    return {
        "name": session.name,
        "dataset": dataset.slug if dataset else None,
        "frame_count": len(dataset.frames) if dataset else 0,
        "status": session.status,
    }
