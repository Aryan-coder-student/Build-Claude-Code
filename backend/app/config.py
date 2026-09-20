"""Backend settings. Override with DEMO_SALES_* environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEMO_SALES_")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'demo_sales.db'}"
    public_url: str = "http://localhost:8000"
    default_tenant_id: str = "ten_demo"
    default_tenant_name: str = "Demo Tenant"
    cors_origins: list[str] = ["*"]

    # LLM enrichment (optional). Credentials resolve via the anthropic SDK (ANTHROPIC_API_KEY etc.).
    llm_enabled: bool = True
    llm_model: str = "claude-opus-5"
    # Required only for API keys that are not scoped to a workspace (Console → Settings → Workspaces).
    anthropic_workspace_id: str = ""

    # Crawler limits
    crawl_max_pages: int = 25
    crawl_page_timeout_ms: int = 15000
    crawl_settle_ms: int = 400
    crawl_networkidle_ms: int = 5000
    crawl_headless: bool = True
    # "http://localhost:3000=http://demo-product:3000,..." — lets the crawler inside Docker reach the product.
    crawl_url_rewrites: str = ""

    def rewrite_crawl_url(self, url: str) -> str:
        for rule in filter(None, self.crawl_url_rewrites.split(",")):
            src, _, dst = rule.partition("=")
            if src and url.startswith(src):
                return dst + url[len(src):]
        return url

    worker_threads: int = 2


settings = Settings()
