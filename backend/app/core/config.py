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
    ZOOM_TOKEN_ENCRYPTION_KEY: str = ""

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""           # Gmail: use an App Password, not your real password
    EMAIL_FROM_NAME: str = "AI Interview Platform"
    EMAIL_FROM: str = "" 

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"
    
    RTMP_SERVER_URL: str = "rtmp://localhost:1935"
    RTMP_STAT_URL: str = "http://localhost:8080/stat"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    class Config:
        env_file = ".env"

settings = Settings()
