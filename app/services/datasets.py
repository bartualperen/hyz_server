import json
import re
import unicodedata
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Dataset, Frame

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TRANSLATION_FILES = ("translations.json", "translation.json")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return value or "dataset"


def scan_images(root: str | Path) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXTS)


def load_translations(root: Path):
    """Varsa translations.json'u okur. Liste (frame sırasına paralel) veya
    dosya-adı→kayıt sözlüğü formatlarını destekler. Yoksa None döner."""
    for fname in TRANSLATION_FILES:
        path = root / fname
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def _coerce_meta(entry) -> tuple[float, float, float, str]:
    if isinstance(entry, dict):
        x = entry.get("translation_x", entry.get("x", 0)) or 0
        y = entry.get("translation_y", entry.get("y", 0)) or 0
        z = entry.get("translation_z", entry.get("z", 0)) or 0
        health = str(entry.get("health_status", entry.get("health", "1")))
    elif isinstance(entry, (list, tuple)):
        vals = list(entry) + [0, 0, 0]
        x, y, z = vals[0], vals[1], vals[2]
        health = "1"
    else:
        x = y = z = 0
        health = "1"
    try:
        return float(x), float(y), float(z), health
    except (TypeError, ValueError):
        return 0.0, 0.0, 0.0, health


def _create_dataset(db, *, slug, name, root, description, video_name, specs) -> Dataset:
    """specs: list of (rel_path, x, y, z, health)."""
    dataset = Dataset(slug=slug, name=name, media_root=str(root), description=description)
    db.add(dataset)
    db.flush()
    for i, (rel, x, y, z, health) in enumerate(specs):
        db.add(
            Frame(
                dataset_id=dataset.id,
                index=i,
                image_url=f"/{slug}/{rel}",
                video_name=video_name,
                gt_translation_x=float(x),
                gt_translation_y=float(y),
                gt_translation_z=float(z),
                health_status=str(health),
            )
        )
    db.commit()
    db.refresh(dataset)
    return dataset


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
    """Açık listelerle dataset kaydı (seed bunu kullanır)."""
    existing = db.scalar(select(Dataset).where(Dataset.slug == slug))
    if existing is not None:
        return existing

    root = Path(media_root).resolve()
    vname = video_name or slug
    specs = []
    for i, img in enumerate(scan_images(root)):
        rel = img.relative_to(root).as_posix()
        tr = translations[i] if translations and i < len(translations) else (0.0, 0.0, 0.0)
        hs = health_statuses[i] if health_statuses and i < len(health_statuses) else "1"
        specs.append((rel, tr[0], tr[1], tr[2], hs))
    return _create_dataset(db, slug=slug, name=name, root=root,
                           description=description, video_name=vname, specs=specs)


def register_dataset_from_path(
    db: Session,
    *,
    path: str,
    name: str | None = None,
    slug: str | None = None,
    description: str = "",
) -> tuple[Dataset, dict]:
    """Panelden kullanılır: bir klasörü tarar, varsa translations.json'u okur,
    dataset + frame kayıtları oluşturur. (dataset, bilgi) döner."""
    root = Path(path).expanduser()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Klasör bulunamadı: {root}")
    root = root.resolve()

    images = scan_images(root)
    if not images:
        raise ValueError(f"Klasörde görsel bulunamadı (jpg/png/...): {root}")

    name = name or root.name
    slug = slugify(slug or name)
    if db.scalar(select(Dataset).where(Dataset.slug == slug)) is not None:
        raise ValueError(f"Bu slug zaten mevcut: '{slug}'")

    translations = load_translations(root)
    specs = []
    for i, img in enumerate(images):
        rel = img.relative_to(root).as_posix()
        entry = None
        if isinstance(translations, dict):
            entry = translations.get(img.name) or translations.get(rel)
        elif isinstance(translations, list) and i < len(translations):
            entry = translations[i]
        x, y, z, health = _coerce_meta(entry)
        specs.append((rel, x, y, z, health))

    dataset = _create_dataset(db, slug=slug, name=name, root=root,
                              description=description, video_name=slug, specs=specs)
    info = {
        "frame_count": len(images),
        "has_translations": translations is not None,
        "slug": slug,
    }
    return dataset, info
