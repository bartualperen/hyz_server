"""Bağımsız örnek dataset üretici (panel/seed olmadan elle çalıştırmak için).

Kullanım:
    python -m scripts.make_sample_dataset --out ./data/media/my_set --count 50
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.sample import generate_sample_images  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Hedef klasör")
    ap.add_argument("--count", type=int, default=30)
    args = ap.parse_args()
    names = generate_sample_images(args.out, args.count)
    print(f"{len(names)} kare üretildi -> {args.out}")


if __name__ == "__main__":
    main()
