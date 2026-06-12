import logging

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import Client, Dataset, EvalSession
from .services.datasets import register_dataset
from .services.sample import generate_sample_images, sample_translations

logger = logging.getLogger("teknofest.seed")

SAMPLE_SLUG = "sample_set"
SAMPLE_SESSION = "sample_session"
SAMPLE_FRAME_COUNT = 30


def run_seed() -> None:
    """AUTO_SEED açıksa: örnek dataset, oturum ve varsayılan client oluşturur.
    Böylece `docker compose up` sonrası istemci hemen test edilebilir."""
    if not settings.auto_seed:
        return

    db = SessionLocal()
    try:
        dataset = db.scalar(select(Dataset).where(Dataset.slug == SAMPLE_SLUG))
        if dataset is None:
            media_dir = settings.media_root_path / SAMPLE_SLUG
            generate_sample_images(media_dir, SAMPLE_FRAME_COUNT)
            translations, health = sample_translations(SAMPLE_FRAME_COUNT)
            dataset = register_dataset(
                db,
                slug=SAMPLE_SLUG,
                name="Örnek Set (otomatik üretildi)",
                media_root=str(media_dir),
                description="AUTO_SEED ile oluşturulan sentetik test seti.",
                video_name=SAMPLE_SLUG,
                translations=translations,
                health_statuses=health,
            )
            logger.info("Örnek dataset oluşturuldu: %s (%d kare)", SAMPLE_SLUG, SAMPLE_FRAME_COUNT)

        session = db.scalar(select(EvalSession).where(EvalSession.name == SAMPLE_SESSION))
        if session is None:
            session = EvalSession(name=SAMPLE_SESSION, dataset_id=dataset.id, status="running")
            db.add(session)
            db.commit()
            db.refresh(session)
            logger.info("Örnek oturum oluşturuldu: %s", SAMPLE_SESSION)

        client = db.scalar(select(Client).where(Client.team_name == settings.default_team_name))
        if client is None:
            client = Client(
                team_name=settings.default_team_name,
                password=settings.default_team_password,
                active_session_id=session.id,
            )
            db.add(client)
            db.commit()
            logger.info("Varsayılan client oluşturuldu: %s", settings.default_team_name)
        elif client.active_session_id is None:
            client.active_session_id = session.id
            db.commit()
    finally:
        db.close()
