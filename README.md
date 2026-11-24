# Lyftr AI — LLM Chatbot with Key Failover and Response Caching

## 1. Live URLs
- Frontend: https://lyftr-ai.netlify.app
- Backend: https://lyftr-ai-sfcf.onrender.com
- Health: `<backend-url>/health`
## 2. Run locally: with Docker and without

### Docker
1. Copy `.env.example` to `.env`.
2. Add at least two valid API keys from the provider selected by `LLM_MODEL`.
3. Run `make up`.
4. Open http://localhost:3000 and check http://localhost:8000/health.
5. Stop with `make down`.

### Without Docker
Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Frontend (new terminal):
```bash
cd frontend
npm install
npm run dev
```
Set `DATABASE_URL`, `LLM_API_KEYS`, `LLM_MODEL`, `ALLOWED_ORIGINS` and `ENABLE_FAILURE_SIMULATION` in the environment.

## 3. Design decisions: key fallback, caching, SQLite session storage
- The backend loads an ordered key pool from `LLM_API_KEYS` and tries the next key when a provider call fails.
- LiteLLM performs model calls and its built-in local cache is enabled. Cache source is reported as `LLM_CACHE` when LiteLLM exposes a cache-hit marker; otherwise the request is reported as `LIVE_INFERENCE`.
- SQLite stores user and assistant messages with assistant metadata. The database is placed under `/data` in Docker and persisted with a named volume.
- Each chat request sends only the new user message; the backend reconstructs prior messages from SQLite.

## 4. Verification: how to see failover, cache hits and per-message token usage
- Health: `GET /health`.
- Chat: `POST /chat` with `{"session_id":"demo-1","message":"Say hello"}`.
- Send the same first message in a different session to test caching.
- Failover: add header `X-Simulate-Failure: key_1=429`; expect a successful answer from key_2.
- All keys fail: add `X-Simulate-Failure: *=429`; expect 503 and no message saved.
- History: `GET /sessions/demo-1/messages`.
- Token counts are stored in assistant metadata per response, not as a conversation total.

Example:
```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"demo-failover","message":"Explain REST in one sentence"}'
```

## 5. Setup Used: your editor and AI tools
- Editor: fill in the editor you used.
- AI tools: disclose the AI tools actually used during development.

## 6. Bonus features (if any): what you added beyond the requirements and why
- Optional system prompt field.
- Responsive chat interface and readable provider errors.

## API contract
- `GET /health`
- `POST /chat`
- `GET /sessions/{session_id}/messages`

Never commit `.env` or real provider keys.
