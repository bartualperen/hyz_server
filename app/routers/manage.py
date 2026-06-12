from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Client, Dataset, EvalSession, Prediction, utcnow
from ..services.datasets import register_dataset_from_path

router = APIRouter(prefix="/manage")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _redirect(path: str, msg: str | None = None, err: str | None = None) -> RedirectResponse:
    params = {}
    if msg:
        params["msg"] = msg
    if err:
        params["err"] = err
    query = ("?" + urlencode(params)) if params else ""
    return RedirectResponse(url=path + query, status_code=303)


def _int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


# --------------------------------------------------------------------------- #
# Datasets
# --------------------------------------------------------------------------- #
@router.get("/datasets", response_class=HTMLResponse, include_in_schema=False)
def datasets_page(request: Request, db: Session = Depends(get_db),
                  msg: str | None = None, err: str | None = None):
    datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    return templates.TemplateResponse(
        request, "manage_datasets.html",
        {"datasets": datasets, "msg": msg, "err": err, "media_root": settings.media_root},
    )


@router.post("/datasets/create", include_in_schema=False)
def datasets_create(
    path: str = Form(...),
    name: str = Form(""),
    slug: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        dataset, info = register_dataset_from_path(
            db, path=path.strip(), name=name.strip() or None,
            slug=slug.strip() or None, description=description.strip(),
        )
    except ValueError as exc:
        return _redirect("/manage/datasets", err=str(exc))
    msg = (f"Dataset '{dataset.slug}' eklendi: {info['frame_count']} kare, "
           f"translations.json: {'var' if info['has_translations'] else 'yok'}.")
    return _redirect("/manage/datasets", msg=msg)


@router.post("/datasets/{dataset_id}/status", include_in_schema=False)
def datasets_status(dataset_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        return _redirect("/manage/datasets", err="Dataset bulunamadı.")
    if status not in ("active", "archived"):
        return _redirect("/manage/datasets", err="Geçersiz durum.")
    dataset.status = status
    db.commit()
    return _redirect("/manage/datasets", msg=f"'{dataset.slug}' durumu: {status}.")


@router.post("/datasets/{dataset_id}/delete", include_in_schema=False)
def datasets_delete(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        return _redirect("/manage/datasets", err="Dataset bulunamadı.")
    session_count = db.scalar(
        select(func.count(EvalSession.id)).where(EvalSession.dataset_id == dataset_id)
    )
    slug = dataset.slug
    db.delete(dataset)  # frame + session + prediction zinciri FK cascade ile silinir
    db.commit()
    extra = f" (+{session_count} session ve tahminleri)" if session_count else ""
    return _redirect("/manage/datasets", msg=f"'{slug}' silindi{extra}.")


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
@router.get("/sessions", response_class=HTMLResponse, include_in_schema=False)
def sessions_page(request: Request, db: Session = Depends(get_db),
                  msg: str | None = None, err: str | None = None):
    sessions = db.scalars(select(EvalSession).order_by(EvalSession.created_at.desc())).all()
    datasets = db.scalars(select(Dataset).order_by(Dataset.name)).all()
    counts = dict(
        db.execute(
            select(Prediction.session_id, func.count(Prediction.id)).group_by(Prediction.session_id)
        ).all()
    )
    return templates.TemplateResponse(
        request, "manage_sessions.html",
        {"sessions": sessions, "datasets": datasets, "counts": counts, "msg": msg, "err": err},
    )


@router.post("/sessions/create", include_in_schema=False)
def sessions_create(name: str = Form(...), dataset_id: int = Form(...), db: Session = Depends(get_db)):
    name = name.strip()
    if not name:
        return _redirect("/manage/sessions", err="Session adı boş olamaz.")
    if db.scalar(select(EvalSession).where(EvalSession.name == name)) is not None:
        return _redirect("/manage/sessions", err=f"'{name}' adlı session zaten var.")
    if db.get(Dataset, dataset_id) is None:
        return _redirect("/manage/sessions", err="Seçilen dataset bulunamadı.")
    db.add(EvalSession(name=name, dataset_id=dataset_id, status="running"))
    db.commit()
    return _redirect("/manage/sessions", msg=f"Session '{name}' oluşturuldu.")


@router.post("/sessions/{session_id}/status", include_in_schema=False)
def sessions_status(session_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    session = db.get(EvalSession, session_id)
    if session is None:
        return _redirect("/manage/sessions", err="Session bulunamadı.")
    if status not in ("running", "completed", "failed"):
        return _redirect("/manage/sessions", err="Geçersiz durum.")
    session.status = status
    session.ended_at = utcnow() if status in ("completed", "failed") else None
    db.commit()
    return _redirect("/manage/sessions", msg=f"'{session.name}' durumu: {status}.")


@router.post("/sessions/{session_id}/delete", include_in_schema=False)
def sessions_delete(session_id: int, db: Session = Depends(get_db)):
    session = db.get(EvalSession, session_id)
    if session is None:
        return _redirect("/manage/sessions", err="Session bulunamadı.")
    name = session.name
    db.delete(session)  # tahminler FK cascade; client.active_session_id SET NULL
    db.commit()
    return _redirect("/manage/sessions", msg=f"Session '{name}' silindi.")


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
@router.get("/clients", response_class=HTMLResponse, include_in_schema=False)
def clients_page(request: Request, db: Session = Depends(get_db),
                 msg: str | None = None, err: str | None = None):
    clients = db.scalars(select(Client).order_by(Client.created_at.desc())).all()
    sessions = db.scalars(select(EvalSession).order_by(EvalSession.created_at.desc())).all()
    counts = dict(
        db.execute(
            select(Prediction.client_id, func.count(Prediction.id)).group_by(Prediction.client_id)
        ).all()
    )
    return templates.TemplateResponse(
        request, "manage_clients.html",
        {"clients": clients, "sessions": sessions, "counts": counts, "msg": msg, "err": err},
    )


@router.post("/clients/create", include_in_schema=False)
def clients_create(
    team_name: str = Form(...),
    password: str = Form(...),
    active_session_id: str = Form(""),
    db: Session = Depends(get_db),
):
    team_name = team_name.strip()
    if not team_name:
        return _redirect("/manage/clients", err="Takım adı boş olamaz.")
    if db.scalar(select(Client).where(Client.team_name == team_name)) is not None:
        return _redirect("/manage/clients", err=f"'{team_name}' zaten var.")
    db.add(Client(team_name=team_name, password=password,
                  active_session_id=_int_or_none(active_session_id)))
    db.commit()
    return _redirect("/manage/clients", msg=f"Client '{team_name}' oluşturuldu.")


@router.post("/clients/{client_id}/assign", include_in_schema=False)
def clients_assign(client_id: int, active_session_id: str = Form(""), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        return _redirect("/manage/clients", err="Client bulunamadı.")
    sid = _int_or_none(active_session_id)
    if sid is not None and db.get(EvalSession, sid) is None:
        return _redirect("/manage/clients", err="Seçilen session bulunamadı.")
    client.active_session_id = sid
    db.commit()
    label = db.get(EvalSession, sid).name if sid else "—"
    return _redirect("/manage/clients", msg=f"'{client.team_name}' aktif session: {label}.")


@router.post("/clients/{client_id}/delete", include_in_schema=False)
def clients_delete(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        return _redirect("/manage/clients", err="Client bulunamadı.")
    name = client.team_name
    db.delete(client)  # tahminlerin client_id'si SET NULL
    db.commit()
    return _redirect("/manage/clients", msg=f"Client '{name}' silindi.")
