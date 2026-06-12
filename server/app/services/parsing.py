import re


def parse_trailing_int(value: str | None) -> int | None:
    """`.../classes/3/` veya `.../frames/12/` gibi URL'lerin sonundaki id'yi ayıklar."""
    if not value:
        return None
    match = re.search(r"(\d+)\s*/?\s*$", value.strip())
    return int(match.group(1)) if match else None


def to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
