from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ANTHROPIC_API_KEY: str = ""
    ZOOM_ACCOUNT_ID: str = ""
    ZOOM_CLIENT_ID: str = ""
    ZOOM_CLIENT_SECRET: str = ""
    ZOOM_WEBHOOK_SECRET: str = ""

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""           # Gmail: use an App Password, not your real password
    EMAIL_FROM_NAME: str = "AI Interview Platform"
    EMAIL_FROM: str = "" 

    class Config:
        env_file = ".env"

settings = Settings()
