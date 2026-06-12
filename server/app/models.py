from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    """Yarışmacı takım / model sürümü. İstemcideki TEAM_NAME buna karşılık gelir."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(256))
    token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, default=None)
    active_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    active_session: Mapped["EvalSession | None"] = relationship(
        foreign_keys=[active_session_id]
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    # Görsellerin bulunduğu mutlak yol. image_url, bu kökten türetilir.
    media_root: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")  # active | archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    frames: Mapped[list["Frame"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", order_by="Frame.index"
    )


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)  # dataset içi sıra
    # /media{image_url} olarak çözülür; mutlaka '/' ile başlar. Örn: /sample_set/frame_000001.jpg
    image_url: Mapped[str] = mapped_column(Text)
    video_name: Mapped[str] = mapped_column(String(256))

    # Pozisyon kestirimi görevi için "ground truth" translation ve health_status.
    gt_translation_x: Mapped[float] = mapped_column(Float, default=0.0)
    gt_translation_y: Mapped[float] = mapped_column(Float, default=0.0)
    gt_translation_z: Mapped[float] = mapped_column(Float, default=0.0)
    health_status: Mapped[str] = mapped_column(String(8), default="1")

    dataset: Mapped["Dataset"] = relationship(back_populates="frames")


class EvalSession(Base):
    """Bir koşum: dataset + (opsiyonel) client. SESSION_NAME bunun adıdır."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="running")  # running | completed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    dataset: Mapped["Dataset"] = relationship()


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        # Aynı client aynı oturumda aynı frame'i tekrar gönderemez (-> 406).
        # Farklı client'lar aynı frame'i gönderebilir (model karşılaştırması için).
        UniqueConstraint("session_id", "client_id", "frame_id", name="uq_prediction_session_client_frame"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
    frame_id: Mapped[int | None] = mapped_column(ForeignKey("frames.id", ondelete="SET NULL"))
    frame_url: Mapped[str] = mapped_column(Text)  # istemcinin gönderdiği ham 'frame' alanı
    raw_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    detected_objects: Mapped[list["DetectedObject"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )
    detected_translations: Mapped[list["DetectedTranslation"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )


class DetectedObject(Base):
    __tablename__ = "detected_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"), index=True)
    cls_api_id: Mapped[int | None] = mapped_column(Integer)  # cls URL'inden parse edilen 1-indeksli id
    cls_index: Mapped[int | None] = mapped_column(Integer)   # 0-indeksli (constants.classes değeri)
    cls_name: Mapped[str | None] = mapped_column(String(32))
    landing_status: Mapped[str | None] = mapped_column(String(8))
    top_left_x: Mapped[float | None] = mapped_column(Float)
    top_left_y: Mapped[float | None] = mapped_column(Float)
    bottom_right_x: Mapped[float | None] = mapped_column(Float)
    bottom_right_y: Mapped[float | None] = mapped_column(Float)

    prediction: Mapped["Prediction"] = relationship(back_populates="detected_objects")


class DetectedTranslation(Base):
    __tablename__ = "detected_translations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"), index=True)
    translation_x: Mapped[float | None] = mapped_column(Float)
    translation_y: Mapped[float | None] = mapped_column(Float)
    translation_z: Mapped[float | None] = mapped_column(Float)

    prediction: Mapped["Prediction"] = relationship(back_populates="detected_translations")


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
    team_name: Mapped[str | None] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(512))
    status_code: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    request_body: Mapped[str | None] = mapped_column(Text)
    response_body: Mapped[str | None] = mapped_column(Text)
