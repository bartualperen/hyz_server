from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Sunucu yapılandırması. Ortam değişkenlerinden (veya .env) okunur."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Veritabanı. Varsayılan SQLite; Postgres için:
    #   postgresql+psycopg://teknofest:teknofest@db:5432/teknofest
    database_url: str = "sqlite:///./data/app.db"

    # İstemciye dağıtılan frame 'url' alanları bu ön ekle üretilir.
    # Görsel ('image_url') ve sınıf ('cls') URL'leri istemcinin kendi base_url'i
    # ile kurulduğundan bu değerin host'u kritik değildir; sondaki '/' önemlidir.
    public_url: str = "http://localhost:8000/"

    # Görsellerin servis edileceği kök dizin. Her dataset'in görselleri
    # MEDIA_ROOT/<dataset_slug>/... altında ya da dataset'in kendi media_root'unda olur.
    media_root: str = "./data/media"

    # Açılışta örnek dataset + varsayılan client/session oluştur.
    auto_seed: bool = True

    # Yarışma kısıtlarını taklit et (frames/translation 5/dk, prediction 80/dk).
    rate_limit_enabled: bool = False

    # AUTO_SEED ile oluşturulacak varsayılan takım.
    default_team_name: str = "test_team"
    default_team_password: str = "test"

    @property
    def public_url_normalized(self) -> str:
        return self.public_url if self.public_url.endswith("/") else self.public_url + "/"

    @property
    def media_root_path(self) -> Path:
        return Path(self.media_root).resolve()


@lru_cache
def get_settings() -> Settings:
    return get_settings_uncached()


def get_settings_uncached() -> Settings:
    return Settings()


settings = get_settings()
