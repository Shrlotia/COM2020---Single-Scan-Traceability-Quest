class Config:
    SECRET_KEY = "dev-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///trace_quest.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False