import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    AI_AGENT_URL = os.getenv("AI_AGENT_URL", "https://azuos-adk-agent-97yo.onrender.com:8000")
    AI_APP_NAME = os.getenv("AI_APP_NAME", "azuos_compliance_beta")
