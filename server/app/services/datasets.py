from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Dataset, Frame

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def scan_images(media_root: str | Path) -> list[Path]:
    root = Path(media_root)
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXTS)


def register_dataset(
    db: Session,
    *,
    slug: str,
    name: str,
    media_root: str | Path,
    description: str = "",
    video_name: str | None = None,
    translations: list[tuple[float, float, float]] | None = None,
    health_statuses: list[str] | None = None,
) -> Dataset:
    """Bir görsel klasörünü tarayıp dataset + frame kayıtları oluşturur.

    image_url her zaman `/<slug>/<media_root'a göre rel yol>` biçiminde olur; bu da
    istemcinin `base_url + 'media' + image_url` ile kuracağı URL'i `/media/<slug>/...`
    yaparak media router'ında çözülür."""
    existing = db.scalar(select(Dataset).where(Dataset.slug == slug))
    if existing is not None:
        return existing

    root = Path(media_root).resolve()
    dataset = Dataset(slug=slug, name=name, media_root=str(root), description=description)
    db.add(dataset)
    db.flush()  # dataset.id

    vname = video_name or slug
    for i, img in enumerate(scan_images(root)):
        rel = img.relative_to(root).as_posix()
        tr = translations[i] if translations and i < len(translations) else (0.0, 0.0, 0.0)
        hs = health_statuses[i] if health_statuses and i < len(health_statuses) else "1"
        db.add(
            Frame(
                dataset_id=dataset.id,
                index=i,
                image_url=f"/{slug}/{rel}",
                video_name=vname,
                gt_translation_x=float(tr[0]),
                gt_translation_y=float(tr[1]),
                gt_translation_z=float(tr[2]),
                health_status=str(hs),
            )
        )

    db.commit()
    db.refresh(dataset)
    return dataset
