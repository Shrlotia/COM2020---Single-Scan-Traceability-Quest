import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///trace_quest.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOW_VERIFIER_SELF_REGISTER = (
        os.environ.get("ALLOW_VERIFIER_SELF_REGISTER", "").strip().lower() == "true"
    )
