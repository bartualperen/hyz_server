from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Dataset

router = APIRouter()


@router.get("/media/{full_path:path}")
def get_media(full_path: str, db: Session = Depends(get_db)):
    """İstemci görseli `base_url + 'media' + image_url` ile ister.
    image_url = `/<dataset_slug>/<rel>` olduğundan ilk segment dataset'i belirler."""
    parts = full_path.split("/", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(status_code=404, detail="Not found.")
    slug, rel = parts

    dataset = db.scalar(select(Dataset).where(Dataset.slug == slug))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    root = Path(dataset.media_root).resolve()
    target = (root / rel).resolve()
    # Path traversal koruması
    if root not in target.parents and target != root:
        raise HTTPException(status_code=403, detail="Forbidden.")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target)
