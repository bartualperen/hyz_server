from pathlib import Path


def generate_sample_images(target_dir: str | Path, count: int = 30, size=(640, 480)) -> list[str]:
    """Test için sentetik JPEG kareler üretir (hareketli kutu + kare numarası)."""
    from PIL import Image, ImageDraw

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    w, h = size
    for i in range(1, count + 1):
        name = f"frame_{i:06d}.jpg"
        path = target / name
        if not path.exists():
            img = Image.new("RGB", size, (28, 30, 42))
            draw = ImageDraw.Draw(img)
            bx = (i * 17) % (w - 90)
            by = (i * 11) % (h - 90)
            draw.rectangle([bx, by, bx + 80, by + 80], outline=(0, 200, 90), width=3)
            draw.text((12, 12), f"frame {i:06d}", fill=(235, 235, 235))
            img.save(path, "JPEG", quality=80)
        names.append(name)
    return names


def sample_translations(count: int):
    """Düz bir yörünge + her 5 karede bir health_status='0' (sistem devrede)."""
    translations: list[tuple[float, float, float]] = []
    health: list[str] = []
    x = y = z = 0.0
    for i in range(count):
        x += 0.5
        y += 0.2
        z += 0.1
        translations.append((round(x, 2), round(y, 2), round(z, 2)))
        health.append("0" if i % 5 == 0 else "1")
    return translations, health
