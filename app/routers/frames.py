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


@router.get("/frames/")
def get_frames(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    if settings.rate_limit_enabled and not rate_limiter.allow((client.id, "frames"), limit=5):
        return JSONResponse(status_code=429, content={"detail": "Request limit exceeded (5/min)."})

    session, dataset = resolve_session(db, client)
    if dataset is None:
        return JSONResponse(
            status_code=409,
            content={"detail": "No active session/dataset for this client. Configure one in the panel."},
        )

    base = settings.public_url_normalized
    return [
        {
            "url": f"{base}frames/{frame.id}/",
            "image_url": frame.image_url,
            "video_name": frame.video_name,
        }
        for frame in dataset.frames
    ]
