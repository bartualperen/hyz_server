from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_client
from ..models import Client
from ..services.context import resolve_session
from ..services.ratelimit import rate_limiter

router = APIRouter()


@router.get("/translation/")
def get_translation(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Frame'lerle AYNI sırada ve uzunlukta translation listesi döner (main.py zip'ler)."""
    if settings.rate_limit_enabled and not rate_limiter.allow((client.id, "translation"), limit=5):
        return JSONResponse(status_code=429, content={"detail": "Request limit exceeded (5/min)."})

    session, dataset = resolve_session(db, client)
    if dataset is None:
        return JSONResponse(
            status_code=409,
            content={"detail": "No active session/dataset for this client. Configure one in the panel."},
        )

    return [
        {
            "translation_x": str(frame.gt_translation_x),
            "translation_y": str(frame.gt_translation_y),
            "translation_z": str(frame.gt_translation_z),
            "health_status": str(frame.health_status),
        }
        for frame in dataset.frames
    ]
