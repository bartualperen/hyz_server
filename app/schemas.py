from pydantic import BaseModel, ConfigDict, Field


# --- İstemci protokolü (gerçek TEKNOFEST sözleşmesi) ---

class AuthIn(BaseModel):
    username: str
    password: str


class AuthOut(BaseModel):
    token: str


class FrameOut(BaseModel):
    url: str
    image_url: str
    video_name: str


class TranslationOut(BaseModel):
    # İstemci string bekliyor (main.py değerleri doğrudan kullanıyor); str olarak döneriz.
    translation_x: str
    translation_y: str
    translation_z: str
    health_status: str


class DetectedObjectIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # cls bir URL'dir: <base>classes/<id>/
    cls: str | None = None
    landing_status: str | None = None
    top_left_x: str | float | None = None
    top_left_y: str | float | None = None
    bottom_right_x: str | float | None = None
    bottom_right_y: str | float | None = None


class DetectedTranslationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    translation_x: str | float | None = None
    translation_y: str | float | None = None
    translation_z: str | float | None = None


class PredictionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    frame: str
    detected_objects: list[DetectedObjectIn] = Field(default_factory=list)
    detected_translations: list[DetectedTranslationIn] = Field(default_factory=list)
