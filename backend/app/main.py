from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.api.routes import zoom_webhook


app = FastAPI(title="Ai interview Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(zoom_webhook.router, prefix=/api)


@app.get("/health")
def health():
    return {"status": "ok"}