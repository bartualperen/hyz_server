"""İstemcideki src/constants.py ile birebir uyumlu sınıf tanımları.

DİKKAT — index/id farkı:
  İstemci, prediction payload'ında cls'i URL olarak gönderir ve id'yi
  `int(class_index) + 1` ile üretir (src/detected_object.py). Yani:
      Tasit(index 0) -> classes/1/
      Insan(index 1) -> classes/2/
      UAP  (index 2) -> classes/3/
      UAI  (index 3) -> classes/4/
  Dolayısıyla /classes/{id}/ endpoint'i 1-indekslidir; index = id - 1.
"""

# index (constants.classes değeri) -> isim
CLASS_NAMES = {
    0: "Tasit",
    1: "Insan",
    2: "UAP",
    3: "UAI",
}

# isim -> index (istemcideki classes sözlüğü)
CLASSES = {name: idx for idx, name in CLASS_NAMES.items()}

LANDING_STATUSES = {
    "Inilebilir": "1",
    "Inilemez": "0",
    "Inis Alani Degil": "-1",
}


def api_id_to_index(api_id: int) -> int | None:
    return api_id - 1 if (api_id - 1) in CLASS_NAMES else None


def index_to_name(index: int | None) -> str | None:
    return CLASS_NAMES.get(index) if index is not None else None
