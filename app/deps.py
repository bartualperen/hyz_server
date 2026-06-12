from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Client, utcnow
from .security import client_from_token


def require_client(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Client:
    client = client_from_token(db, authorization)
    if client is None:
        # Django REST'in döndürdüğü mesaja yakın tutuldu.
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials were not provided.",
        )
    client.last_seen_at = utcnow()
    db.commit()
    return client
