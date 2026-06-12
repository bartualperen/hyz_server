import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Client
from ..security import generate_token

logger = logging.getLogger("teknofest.auth")
router = APIRouter()


@router.post("/auth/")
def auth(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """İstemci `data={'username','password'}` (form) gönderir, `{'token': ...}` bekler (200)."""
    client = db.scalar(select(Client).where(Client.team_name == username))

    if client is None:
        # Lokal test kolaylığı: bilinmeyen takımı ilk auth'ta otomatik oluştur.
        client = Client(team_name=username, password=password)
        db.add(client)
        logger.info("Yeni client otomatik oluşturuldu: %s", username)
    elif client.password != password:
        return JSONResponse(status_code=400, content={"detail": "Invalid username or password."})

    client.token = generate_token()
    db.commit()
    db.refresh(client)
    return JSONResponse(status_code=200, content={"token": client.token})
