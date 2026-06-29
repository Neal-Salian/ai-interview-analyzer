# Deployment Troubleshooting Guide

## Health Endpoint Reference

### `GET /health`

The health endpoint probes all three subsystems and returns their status:

```json
{
  "status": "healthy",
  "database": true,
  "ollama": true,
  "rtmp": true,
  "active_sessions": 2,
  "uptime_seconds": 3600.5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `"healthy"` \| `"degraded"` | `"healthy"` only when all three subsystems are `true` |
| `database` | `bool` | PostgreSQL reachable via `SELECT 1` |
| `ollama` | `bool` | Ollama API responding on `localhost:11434` |
| `rtmp` | `bool` | nginx-rtmp stats page responding on `localhost:8080` |
| `active_sessions` | `int` | Number of currently active interview sessions |
| `uptime_seconds` | `float` | Seconds since the FastAPI server started |

> **Note**: The endpoint always returns HTTP 200 so Docker/k8s healthchecks pass
> even when degraded. Use the `status` field to distinguish health states.

---

## Common Failure Scenarios

### Database Unreachable (`"database": false`)

**Symptoms**: `/health` returns `"database": false`, API routes return 500 errors.

**Diagnosis**:
```bash
# Check if PostgreSQL container is running
docker ps | grep interview_db

# Check PostgreSQL logs
docker logs interview_db --tail 50

# Test direct connectivity
docker exec interview_db pg_isready -U postgres
```

**Common Causes**:
- PostgreSQL container not started: `docker compose up -d db`
- Connection string mismatch: verify `DATABASE_URL` in `.env` matches `docker-compose.yml` port mapping (host `5434` → container `5432`)
- Database ran out of disk: check `docker system df`

---

### Ollama Not Running (`"ollama": false`)

**Symptoms**: `/health` returns `"ollama": false`, question generation returns empty results, explanations return "Explanation service is not available."

**Diagnosis**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If using Docker
docker ps | grep ollama

# Check Ollama logs
ollama logs
```

**Common Causes**:
- Ollama not installed or not started: `ollama serve`
- Model not pulled: `ollama pull llama3.1:8b` (Ensure `OLLAMA_MODEL` in `.env` matches the pulled model exactly)
- Port conflict: another service on port 11434
- GPU out of memory: check `nvidia-smi` or reduce model size
- Docker networking issue: The backend container cannot reach `localhost:11434` on the host unless configured properly.

### Supported Ollama Deployment Configurations
Ensure your `.env` overrides `OLLAMA_BASE_URL` depending on your environment:

1. **Local Development (No Docker)**
   - `OLLAMA_BASE_URL=http://localhost:11434`
2. **Docker Desktop (Mac/Windows)**
   - `OLLAMA_BASE_URL=http://host.docker.internal:11434`
3. **Docker on Linux / External Server**
   - `OLLAMA_BASE_URL=http://172.17.0.1:11434` (or exact host IP)
4. **Containerized Ollama (if added to docker-compose.yml)**
   - `OLLAMA_BASE_URL=http://ollama:11434`

> **Impact**: Ollama being down does NOT block interview recording or analysis.
> Only real-time question generation and metric explanations are affected.

---

### RTMP Subsystem Down (`"rtmp": false`)

**Symptoms**: `/health` returns `"rtmp": false`, live interview streams fail to connect, consumer logs show "Failed to open stream."

**Diagnosis**:
```bash
# Check if nginx-rtmp container is running
docker ps | grep nginx_rtmp

# Check nginx-rtmp logs
docker logs nginx_rtmp --tail 50

# Test stats endpoint
curl http://localhost:8080/stat

# Test RTMP port directly
nc -z localhost 1935 && echo "RTMP port open" || echo "RTMP port closed"
```

**Common Causes**:
- nginx-rtmp container not started: `docker compose up -d nginx-rtmp`
- Port 1935 or 8080 blocked by firewall
- Invalid `nginx-rtmp.conf`: check `docker logs nginx_rtmp` for config parse errors

---

## Log Event Reference

All structured events are emitted as JSON lines in production and human-readable strings in development.

| Event | Severity | When | Key Fields |
|-------|----------|------|------------|
| `meeting_started` | INFO | Zoom webhook fires `meeting.started` | `session_id`, `meeting_id`, `is_orphan` |
| `meeting_ended` | INFO | Zoom webhook fires `meeting.ended` | `session_id`, `meeting_id` |
| `session_scheduled` | INFO | Session created or draft session scheduled | `session_id`, `candidate_name` |
| `report_generated` | INFO | Report generator builds full report | `session_id`, `sections_count` |
| `consumer_started` | INFO | RTMP consumer successfully opens stream | `session_id`, `rtmp_url` |
| `consumer_failed` | ERROR | RTMP consumer fails to open stream | `session_id`, `error_type`, `error_message` |

### Searching Logs

```bash
# Find all meeting starts
grep '"event": "meeting_started"' backend.log

# Find failed consumers
grep '"event": "consumer_failed"' backend.log

# Find orphan sessions (no pre-scheduled session matched)
grep '"is_orphan": true' backend.log

# Count active sessions over time
grep '"event": "meeting_started"\|"event": "meeting_ended"' backend.log
```

---

## Docker Healthcheck Behavior

The backend service in `docker-compose.yml` has a healthcheck configured:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

- The healthcheck hits `GET /health` every 30 seconds
- It checks for an HTTP 200 response (which is always returned)
- After 3 consecutive failures (unlikely unless the process is completely unresponsive), Docker marks the container as unhealthy
- The `start_period` of 60 seconds gives Alembic migrations and model loading time to complete

---

## Checking Active Sessions

### Via Health Endpoint

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```

The `active_sessions` field shows how many consumers are currently running.

### Via Application Logs

```bash
# Find all currently active sessions (started but not ended)
grep '"event": "meeting_started"' backend.log | tail -20

# Check for consumer failures
grep '"event": "consumer_failed"' backend.log | tail -10
```

---

## Environment-Specific Log Format

| Environment | Format | Example |
|-------------|--------|---------|
| `development` | Human-readable | `2026-06-25 08:30:00 INFO     [app.api.routes.zoom_webhook] meeting_started \| session_id=abc meeting_id=123` |
| `production` | JSON lines | `{"timestamp": "2026-06-25T08:30:00+00:00", "level": "INFO", "event": "meeting_started", "session_id": "abc", "meeting_id": "123"}` |

Controlled by the `ENV` setting in `.env`:
```env
ENV=development   # human-readable logs
ENV=production    # JSON-line logs
```
