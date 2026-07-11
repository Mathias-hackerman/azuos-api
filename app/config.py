import os
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _normalize_agent_url(raw_url: str | None) -> str:
    default_url = "https://azuos-adk-agent-97yo.onrender.com"
    if not raw_url:
        return default_url

    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"

    parsed = urlsplit(raw_url)
    if parsed.hostname and parsed.hostname.endswith(".onrender.com"):
        netloc = parsed.hostname
        if parsed.username:
            netloc = parsed.username
            if parsed.password:
                netloc += f":{parsed.password}"
            netloc += f"@{parsed.hostname}"
        return urlunsplit((parsed.scheme, netloc, parsed.path.rstrip("/"), parsed.query, parsed.fragment))

    return raw_url.rstrip("/")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    AI_AGENT_URL = _normalize_agent_url(os.getenv("AI_AGENT_URL"))
    AI_APP_NAME = os.getenv("AI_APP_NAME", "azuos_compliance_beta")
