import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Client


def generate_token() -> str:
    return secrets.token_hex(20)


def parse_token_header(authorization: str | None) -> str | None:
    """`Authorization: Token <token>` başlığından token'ı ayıkla."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "token":
        return parts[1]
    if len(parts) == 1:
        return parts[0]
    return None


def client_from_token(db: Session, authorization: str | None) -> Client | None:
    token = parse_token_header(authorization)
    if not token:
        return None
    return db.scalar(select(Client).where(Client.token == token))
