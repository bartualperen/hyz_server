import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..constants import api_id_to_index, index_to_name
from ..database import get_db
from ..deps import require_client
from ..models import Client, DetectedObject, DetectedTranslation, Prediction
from ..schemas import PredictionIn
from ..services.context import resolve_session
from ..services.parsing import parse_trailing_int, to_float
from ..services.ratelimit import rate_limiter

router = APIRouter()


@router.post("/prediction/")
def post_prediction(
    payload: PredictionIn,
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    session, dataset = resolve_session(db, client)
    if session is None:
        return JSONResponse(
            status_code=409,
            content={"detail": "No active session for this client. Configure one in the panel."},
        )

    # Yarışma kısıtı: 80 frame/dk. Aşımda DB'ye YAZILMAZ ve Django-stili cevap döner.
    if settings.rate_limit_enabled and not rate_limiter.allow((client.id, "prediction"), limit=80):
        return JSONResponse(
            status_code=403,
            content={"detail": "You do not have permission to perform this action."},
        )

    frame_id = parse_trailing_int(payload.frame)

    # Aynı client aynı oturumda aynı frame'i ikinci kez gönderirse -> 406 (istemci tekrar denemez).
    dup_query = select(Prediction).where(
        Prediction.session_id == session.id,
        Prediction.client_id == client.id,
    )
    if frame_id is not None:
        dup_query = dup_query.where(Prediction.frame_id == frame_id)
    else:
        dup_query = dup_query.where(Prediction.frame_url == payload.frame)
    if db.scalar(dup_query) is not None:
        return JSONResponse(
            status_code=406,
            content={"detail": "Prediction for this frame already exists in this session."},
        )

    prediction = Prediction(
        session_id=session.id,
        client_id=client.id,
        frame_id=frame_id,
        frame_url=payload.frame,
        raw_payload=json.dumps(payload.model_dump(), ensure_ascii=False),
    )

    for obj in payload.detected_objects:
        api_id = parse_trailing_int(obj.cls)
        index = api_id_to_index(api_id) if api_id is not None else None
        prediction.detected_objects.append(
            DetectedObject(
                cls_api_id=api_id,
                cls_index=index,
                cls_name=index_to_name(index),
                landing_status=str(obj.landing_status) if obj.landing_status is not None else None,
                top_left_x=to_float(obj.top_left_x),
                top_left_y=to_float(obj.top_left_y),
                bottom_right_x=to_float(obj.bottom_right_x),
                bottom_right_y=to_float(obj.bottom_right_y),
            )
        )

    for tr in payload.detected_translations:
        prediction.detected_translations.append(
            DetectedTranslation(
                translation_x=to_float(tr.translation_x),
                translation_y=to_float(tr.translation_y),
                translation_z=to_float(tr.translation_z),
            )
        )

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # İstemci 201'i başarı sayar.
    return JSONResponse(
        status_code=201,
        content={"status": "ok", "prediction_id": prediction.id},
    )
