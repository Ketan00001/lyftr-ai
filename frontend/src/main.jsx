import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Bot, Send, Sparkles, User, RefreshCw } from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const newSession = () => "s-" + crypto.randomUUID();
function App() {
  const [sessionId] = useState(() => {
  const saved = localStorage.getItem("lyftr_session_id");
  if (saved) return saved;

  const id = newSession();
  localStorage.setItem("lyftr_session_id", id);
  return id;
});
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);
  useEffect(() => {
  async function loadHistory() {
    try {
      const res = await fetch(`${API}/sessions/${sessionId}/messages`);

      if (res.status === 404) return;
      if (!res.ok) throw new Error("Unable to load chat history");

      const data = await res.json();
      setMessages(data.messages || []);
    } catch (e) {
      console.error("History loading failed:", e);
    }
  }

  loadHistory();
}, [sessionId]);
  useEffect(() => {
  if (bottom.current) {
    bottom.current.scrollIntoView({ behavior: "smooth" });
  }
}, [messages, busy]);

  async function send() {
    const message = input.trim();
    if (!message || busy) return;
    setInput(""); setError("");
    setMessages(old => [...old, { role: "user", content: message }]);
    setBusy(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message, ...(systemPrompt.trim() ? { system_prompt: systemPrompt.trim() } : {}) })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
      setMessages(old => [...old, { role: "assistant", content: data.reply, metadata: data.metadata }]);
    } catch (e) {
      setError(e.message || "Unable to connect to the backend.");
    } finally { setBusy(false); }
  }
  function onKey(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }
  return <div className="shell">
    <header><div className="brand"><div className="logo"><Sparkles size={21}/></div><div><b>Lyftr AI</b><small>Full-stack intelligent assistant</small></div></div><span className="online">● API chat</span></header>
    <main>
      <div className="welcome"><div className="hero-icon"><Bot size={30}/></div><h1>What can I help you with?</h1><p>Ask anything. Your conversation stays in this session.</p></div>
      <label className="prompt-label" htmlFor="system-prompt-input">System prompt <span>Optional</span></label>
      <input id="system-prompt-input" data-testid="system-prompt-input" className="system-input" value={systemPrompt} onChange={e=>setSystemPrompt(e.target.value)} placeholder="e.g. You are a concise coding tutor"/>
      <section className="conversation">
        {messages.map((m,i)=><div className={`message ${m.role}`} key={i} data-testid={m.role === "assistant" ? "assistant-message" : undefined}>
          <div className="avatar">{m.role==="assistant"?<Bot size={17}/>:<User size={17}/>}</div>
          <div className="bubble"><div className="message-text">{m.content}</div>
            {m.role==="assistant" && <div className="metadata">
              <span data-testid="meta-source" className={m.metadata?.resolution_source==="LLM_CACHE"?"cache":""}>{m.metadata?.resolution_source}</span>
              <span data-testid="meta-model">Model: {m.metadata?.model}</span>
              <span data-testid="meta-latency">{m.metadata?.latency_ms} ms</span>
              <span>In: <b data-testid="meta-input-tokens">{m.metadata?.input_tokens}</b></span>
              <span>Out: <b data-testid="meta-output-tokens">{m.metadata?.output_tokens}</b></span>
              {m.metadata?.key_id && <span>{m.metadata.key_id}</span>}
              {m.metadata?.fallback_attempts > 0 && <span>Fallbacks: {m.metadata.fallback_attempts}</span>}
            </div>}
          </div>
        </div>)}
        {busy && <div className="typing"><Bot size={17}/> Thinking…</div>}
        {error && <div className="error"><b>Request failed:</b> {error}</div>}
        <div ref={bottom}/>
      </section>
    </main>
    <footer><div className="composer"><textarea data-testid="chat-input" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={onKey} placeholder="Message Lyftr AI…" rows="1"/><button data-testid="send-button" onClick={send} disabled={!input.trim()||busy} aria-label="Send message"><Send size={18}/></button></div><small>Enter to send · Shift + Enter for a new line · Session {sessionId.slice(0,12)}</small></footer>
  </div>;
}
createRoot(document.getElementById("root")).render(<App/>);
