from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Azure OpenAI (GPT-4o Vision / Embeddings)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_vision_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_api_version: str = "2024-06-01"

    # CORS（カンマ区切りで複数指定可）
    cors_allow_origins: list[str] = ["http://localhost:5173"]

    # 外部API（無料のデモ/公開インスタンス。将来的に自前ホストや商用APIへ差し替える）
    # OSRM公開デモサーバーは車プロファイルのみ実質稼働・商用利用不可。
    # 本番運用時は自前ホストのOSRM（foot profile）等に差し替えること。
    osrm_base_url: str = "https://router.project-osrm.org/route/v1"
    osrm_profile: str = "foot"
    overpass_api_url: str = "https://overpass-api.de/api/interpreter"
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    # ジオコーディングの検索対象国（カンマ区切り。空文字で制限なし）
    nominatim_country_codes: str = "jp"

    # HTTPクライアント
    http_timeout_s: float = 10.0
    http_max_retries: int = 2
    nominatim_min_interval_s: float = 1.0

    # 画像アップロード制限
    max_image_size_bytes: int = 10 * 1024 * 1024  # 10MB
    max_images_per_report: int = 5

    # ログレベル
    log_level: str = "INFO"

    # 通報管理API（PATCH /api/reports/{id}/status）の管理者トークン。
    # 未設定（空文字）の場合はトークンの値に関わらず常に401を返す。
    admin_token: str = ""

    # Google Maps Platform（Routes API・Places API (New)）。
    # 設定時はルート検索・地点検索がGoogleに切り替わる。未設定時は既存のOSRM/Nominatimで動作する。
    google_maps_api_key: str = ""


settings = Settings()
