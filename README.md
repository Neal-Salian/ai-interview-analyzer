# AI Interview Analyzer

A real-time behavioral and psychometric analytics platform for video-based interviews. The system streams live interview footage, analyzes facial emotions and speech patterns in real time, and surfaces intelligent follow-up questions — giving recruiters deep candidate insights as the interview unfolds.

---

## What it does

- **Live emotion detection** — analyzes candidate facial expressions frame by frame during the interview using DeepFace
- **Real-time speech transcription** — converts candidate speech to text in 30-second chunks using OpenAI Whisper, running fully locally
- **AI-generated follow-up questions** — after each candidate response, Claude API suggests 3 relevant follow-up questions for the recruiter based on what the candidate just said
- **Psychometric scoring** — estimates Big Five personality traits (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) from transcript text
- **Sentiment analysis** — tracks candidate sentiment arc across the full interview timeline
- **Speech metrics** — words per minute, filler word count, confidence indicators
- **Live recruiter dashboard** — all analytics update in real time via WebSocket during the interview
- **Post-interview PDF report** — auto-generated after the call with full scores, transcript, emotion timeline, and AI-written summary
- **Candidate comparison** — side-by-side score comparison across multiple candidates

---

## Architecture

```
Zoom meeting
    │
    ▼ RTMP live stream
nginx-rtmp server (port 1935)
    │
    ├── video frames ──▶ DeepFace ──▶ emotion scores ──▶ PostgreSQL
    │
    └── audio chunks ──▶ Whisper ──▶ transcript ──▶ Claude API ──▶ suggested questions
                                          │
                                          ▼
                                   HuggingFace NLP
                                   (sentiment + Big Five)
                                          │
                                          ▼
                                     PostgreSQL
                                          │
                                          ▼
                              WebSocket ──▶ Recruiter dashboard
```

All AI/ML processing runs **fully locally** on the server. No candidate audio, video, or transcript is ever sent to an external API. The only external call is to Claude API for question generation and report summarisation, which receives only anonymised context — never raw candidate data.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Live streaming | Zoom RTMP, nginx-rtmp, PyAV |
| Emotion detection | DeepFace, OpenCV |
| Speech transcription | OpenAI Whisper (local) |
| NLP & psychometrics | HuggingFace Transformers |
| LLM | Anthropic Claude API |
| Frontend | React, TypeScript, Vite, Recharts |
| Database | PostgreSQL 15 |
| Infrastructure | Docker, Docker Compose |
| Auth | JWT, bcrypt, role-based access control |

---

## Getting started

### Prerequisites

- Docker Desktop
- Python 3.11
- Node.js 20 LTS
- A Zoom Server-to-Server OAuth app ([marketplace.zoom.us](https://marketplace.zoom.us))
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone the repo

```bash
git clone https://github.com/Neal-Salian/ai-interview-analyzer.git
cd ai-interview-analyzer
```

### 2. Set up environment variables

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in your values:

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/interviewer
SECRET_KEY=your-random-secret-key
ALGORITHM=HS256
ANTHROPIC_API_KEY=sk-ant-xxxx
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret
ZOOM_WEBHOOK_SECRET=your-webhook-secret
```

### 3. Start infrastructure

```bash
docker compose up db nginx-rtmp -d
```

### 4. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`
Interactive API docs at `http://localhost:8000/docs`

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## Project structure

```
ai-interview-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # FastAPI route handlers
│   │   │   └── websocket.py     # WebSocket broadcaster
│   │   ├── ml/
│   │   │   ├── emotion/         # DeepFace wrapper
│   │   │   ├── speech/          # Whisper transcription
│   │   │   ├── nlp/             # Sentiment, Big Five, psychometrics
│   │   │   ├── llm/             # Claude API — question generation
│   │   │   ├── stream/          # RTMP consumer, frame + audio processor
│   │   │   └── report/          # PDF generation
│   │   ├── db/                  # SQLAlchemy models, schemas, CRUD
│   │   ├── core/                # Config, security, logging
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, SessionReport, Login
│   │   ├── components/          # Charts, cards, Q&A panel
│   │   ├── hooks/               # useWebSocket
│   │   ├── api/                 # Typed API client
│   │   └── types/
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## How the live Q&A system works

Every 30 seconds, Whisper transcribes the latest audio chunk from the live stream. The transcript is saved to the database and immediately sent to Claude API with the prompt:

> *"Based on what the candidate just said, suggest 3 relevant follow-up questions the recruiter should ask next."*

The suggested questions appear on the recruiter's dashboard in real time. The recruiter can click "asked" to mark a question as used — this is tracked in the database and included in the final PDF report, showing which AI-suggested questions were actually asked during the interview.

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/auth/login` | Recruiter login, returns JWT |
| POST | `/api/candidates` | Register a candidate |
| POST | `/api/sessions` | Create a new interview session |
| PATCH | `/api/sessions/{id}/end` | End a session |
| GET | `/api/analysis/{session_id}` | Get full post-interview analytics |
| POST | `/api/qna/suggest/{session_id}` | Get AI-suggested follow-up questions |
| GET | `/api/reports/{session_id}` | Download PDF report |
| WS | `/ws/live/{session_id}` | WebSocket — live emotion + transcript feed |
| POST | `/webhook/zoom` | Zoom webhook receiver |

---

## Security

- All candidate video and audio is processed in memory — raw frames are never written to disk
- Whisper and DeepFace run entirely locally — no biometric data leaves the server
- JWT authentication required on every API route
- Role-based access control — recruiters can only access their own sessions
- Database credentials use a restricted app user, not the postgres superuser
- All passwords hashed with bcrypt
- Audit log records every login, report view, and session access event
- Rate limiting on authentication endpoints (5 attempts per minute)

---

## Known limitations

- Emotion detection accuracy drops in low-light conditions or at extreme camera angles
- Whisper `base` model works well for English; use `small` or `medium` for better Hindi accuracy
- Concurrent session limit of ~5 on a CPU-only server — GPU recommended for production
- RTMP stream requires a publicly accessible server IP (use ngrok for local development)

---

## References

- Naim et al., *Automated Analysis and Prediction of Job Interview Performance* — arXiv:1504.03425 (2015)
- Nguyen & Gatica-Perez, *Hire Me: Computational Inference of Hirability* — IEEE Transactions on Multimedia (2014)
- Radford et al., *Robust Speech Recognition via Large-Scale Weak Supervision* — arXiv:2212.04356 (2022)
- Serengil & Ozpinar, *LightFace: A Hybrid Deep Face Recognition Framework* — ASYU (2020)
- Mairesse et al., *Using Linguistic Cues for the Automatic Recognition of Personality* — JAIR, 30:457–500 (2007)

---

## License

MIT
