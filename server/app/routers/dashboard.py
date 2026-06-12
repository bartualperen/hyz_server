from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Client,
    Dataset,
    EvalSession,
    Frame,
    Prediction,
    RequestLog,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = {
        "datasets": db.scalar(select(func.count(Dataset.id))),
        "sessions": db.scalar(select(func.count(EvalSession.id))),
        "clients": db.scalar(select(func.count(Client.id))),
        "frames": db.scalar(select(func.count(Frame.id))),
        "predictions": db.scalar(select(func.count(Prediction.id))),
        "requests": db.scalar(select(func.count(RequestLog.id))),
    }
    datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    sessions = db.scalars(select(EvalSession).order_by(EvalSession.created_at.desc())).all()
    clients = db.scalars(select(Client).order_by(Client.created_at.desc())).all()
    recent_predictions = db.scalars(
        select(Prediction).order_by(Prediction.created_at.desc()).limit(15)
    ).all()
    recent_logs = db.scalars(
        select(RequestLog).order_by(RequestLog.created_at.desc()).limit(20)
    ).all()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "datasets": datasets,
            "sessions": sessions,
            "clients": clients,
            "recent_predictions": recent_predictions,
            "recent_logs": recent_logs,
        },
    )


@router.get("/dashboard/predictions/{prediction_id}", response_class=HTMLResponse, include_in_schema=False)
def prediction_detail(prediction_id: int, request: Request, db: Session = Depends(get_db)):
    prediction = db.get(Prediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    frame = db.get(Frame, prediction.frame_id) if prediction.frame_id else None
    media_src = ("/media" + frame.image_url) if frame else None
    return templates.TemplateResponse(
        request,
        "prediction_detail.html",
        {"prediction": prediction, "frame": frame, "media_src": media_src},
    )


@router.get("/dashboard/logs", response_class=HTMLResponse, include_in_schema=False)
def logs(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(RequestLog).order_by(RequestLog.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "logs.html", {"logs": rows})
