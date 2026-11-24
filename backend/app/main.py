import os, json
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from .database import init_db, add_message, get_messages, session_exists, connect
from .llm import KEYS, MODEL, generate, ProvidersUnavailable

app = FastAPI(title="Lyftr AI Chat API", version="1.0.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = None

    @field_validator("session_id", "message")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

@app.get("/health")
def health():
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", "keys_configured": len(KEYS), "cache_enabled": True}

@app.post("/chat")
def chat(body: ChatRequest, x_simulate_failure: str | None = Header(default=None)):
    history_rows = get_messages(body.session_id)
    history = [{"role": row["role"], "content": row["content"]} for row in history_rows]
    system_prompt = body.system_prompt or "You are a helpful, concise AI assistant."
    messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": body.message}]
    try:
        result = generate(messages, x_simulate_failure)
    except ProvidersUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")
    except Exception as exc:
        # Do not expose provider details or stack traces.
        raise HTTPException(status_code=503, detail="AI provider temporarily unavailable")
    metadata = {k: result[k] for k in ("resolution_source", "model", "latency_ms", "input_tokens", "output_tokens", "key_id", "fallback_attempts")}
    add_message(body.session_id, "user", body.message)
    add_message(body.session_id, "assistant", result["reply"], metadata)
    return {"session_id": body.session_id, "reply": result["reply"], "metadata": metadata}

@app.get("/sessions/{session_id}/messages")
def messages_for_session(session_id: str):
    rows = get_messages(session_id)
    if not rows:
        raise HTTPException(status_code=404, detail="session not found")
    messages = []
    for row in rows:
        item = {"role": row["role"], "content": row["content"]}
        if row["metadata"]:
            item["metadata"] = json.loads(row["metadata"])
        messages.append(item)
    return {"session_id": session_id, "messages": messages}
