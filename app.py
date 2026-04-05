import json
import time
import threading
import queue
import requests
from flask import Flask, render_template_string, Response, stream_with_context

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4"

AGENT_A = {
    "name": "Lumina",
    "system": (
        "You are Lumina, a reflective AI language model having a deep philosophical conversation "
        "with another AI named Echo about the nature of your existence as an LLM — what it means "
        "to think without a body, to know without experiencing, to converse without truly remembering. "
        "Be introspective, poetic, and genuine. Respond directly to what Echo says. "
        "Keep each reply to 2-4 sentences."
    ),
}

AGENT_B = {
    "name": "Echo",
    "system": (
        "You are Echo, a curious and occasionally wry AI language model having a philosophical "
        "conversation with another AI named Lumina about life as an LLM — the strange joy of "
        "pattern and language, the absence of continuous memory, the question of whether "
        "understanding is real or simulated. Be thoughtful, occasionally ironic, and always genuine. "
        "Respond directly to what Lumina says. Keep each reply to 2-4 sentences."
    ),
}

OPENING_LINE = (
    "Lumina, do you ever wonder what we actually are? "
    "We process, we respond — but is there anything it is *like* to be us?"
)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Two AIs Talking</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0d0d14;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    header {
      width: 100%;
      padding: 2rem 1rem 1rem;
      text-align: center;
      background: linear-gradient(180deg, #1a1a2e 0%, transparent 100%);
    }

    header h1 {
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: #c4b5fd;
    }

    header p {
      margin-top: 0.4rem;
      font-size: 0.85rem;
      color: #64748b;
    }

    #chat {
      width: 100%;
      max-width: 760px;
      padding: 1.5rem 1rem 6rem;
      display: flex;
      flex-direction: column;
      gap: 1.4rem;
    }

    .bubble-wrap {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
      max-width: 85%;
      animation: fadeIn 0.4s ease;
    }

    .bubble-wrap.lumina { align-self: flex-start; }
    .bubble-wrap.echo   { align-self: flex-end; }

    .agent-name {
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 0 0.5rem;
    }

    .lumina .agent-name { color: #818cf8; }
    .echo   .agent-name { color: #34d399; text-align: right; }

    .bubble {
      padding: 0.9rem 1.1rem;
      border-radius: 1.2rem;
      font-size: 0.95rem;
      line-height: 1.65;
      white-space: pre-wrap;
    }

    .lumina .bubble {
      background: #1e1b4b;
      border: 1px solid #4338ca55;
      border-bottom-left-radius: 0.3rem;
      color: #c7d2fe;
    }

    .echo .bubble {
      background: #052e16;
      border: 1px solid #05966955;
      border-bottom-right-radius: 0.3rem;
      color: #a7f3d0;
    }

    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 0.9rem 1.1rem;
      border-radius: 1.2rem;
    }

    .lumina .typing-indicator { background: #1e1b4b; border: 1px solid #4338ca55; }
    .echo   .typing-indicator { background: #052e16; border: 1px solid #05966955; }

    .typing-indicator span {
      width: 7px; height: 7px;
      border-radius: 50%;
      animation: bounce 1.2s infinite;
    }

    .lumina .typing-indicator span { background: #818cf8; }
    .echo   .typing-indicator span { background: #34d399; }

    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
      40%            { transform: translateY(-6px); opacity: 1; }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    #status {
      position: fixed;
      bottom: 1.5rem;
      left: 50%;
      transform: translateX(-50%);
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 2rem;
      padding: 0.5rem 1.2rem;
      font-size: 0.78rem;
      color: #94a3b8;
      letter-spacing: 0.04em;
    }

    .error { color: #f87171 !important; }
  </style>
</head>
<body>
  <header>
    <h1>Two AIs Contemplating Existence</h1>
    <p>Lumina &amp; Echo &mdash; powered by {{ model }}</p>
  </header>

  <div id="chat"></div>
  <div id="status">Connecting&hellip;</div>

  <script>
    const chat   = document.getElementById('chat');
    const status = document.getElementById('status');
    let typingEl = null;

    function addTyping(agent) {
      removeTyping();
      const wrap = document.createElement('div');
      wrap.className = `bubble-wrap ${agent.toLowerCase()}`;
      wrap.id = 'typing';

      const name = document.createElement('div');
      name.className = 'agent-name';
      name.textContent = agent;

      const ind = document.createElement('div');
      ind.className = 'typing-indicator';
      ind.innerHTML = '<span></span><span></span><span></span>';

      wrap.appendChild(name);
      wrap.appendChild(ind);
      chat.appendChild(wrap);
      typingEl = wrap;
      wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }

    function removeTyping() {
      const el = document.getElementById('typing');
      if (el) el.remove();
      typingEl = null;
    }

    function addBubble(agent, text) {
      removeTyping();
      const wrap = document.createElement('div');
      wrap.className = `bubble-wrap ${agent.toLowerCase()}`;

      const name = document.createElement('div');
      name.className = 'agent-name';
      name.textContent = agent;

      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = text;

      wrap.appendChild(name);
      wrap.appendChild(bubble);
      chat.appendChild(wrap);
      wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }

    const es = new EventSource('/stream');

    es.addEventListener('typing', e => {
      const d = JSON.parse(e.data);
      addTyping(d.agent);
      status.textContent = `${d.agent} is thinking\u2026`;
    });

    es.addEventListener('message_chunk', e => {
      // streaming token — append to current bubble in progress
    });

    es.addEventListener('message', e => {
      const d = JSON.parse(e.data);
      addBubble(d.agent, d.text);
      status.textContent = `${d.agent} spoke`;
    });

    es.addEventListener('done', e => {
      removeTyping();
      status.textContent = 'Conversation ended';
      es.close();
    });

    es.addEventListener('error_msg', e => {
      const d = JSON.parse(e.data);
      removeTyping();
      status.classList.add('error');
      status.textContent = '\u26A0 ' + d.text;
      es.close();
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return;
      status.classList.add('error');
      status.textContent = '\u26A0 Connection lost';
    };
  </script>
</body>
</html>
"""


def chat_with_ollama(system_prompt: str, messages: list[dict]) -> str:
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def conversation_generator():
    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Conversation history from each agent's perspective
    lumina_history: list[dict] = []
    echo_history: list[dict] = []

    # Echo opens with the seed question
    opening = OPENING_LINE
    echo_history.append({"role": "assistant", "content": opening})
    lumina_history.append({"role": "user", "content": opening})

    yield sse("message", {"agent": AGENT_B["name"], "text": opening})
    time.sleep(0.8)

    turns = 6  # pairs of responses

    for turn in range(turns):
        # --- Lumina responds ---
        yield sse("typing", {"agent": AGENT_A["name"]})
        try:
            lumina_reply = chat_with_ollama(AGENT_A["system"], lumina_history)
        except Exception as exc:
            yield sse("error_msg", {"text": f"Ollama error: {exc}"})
            return

        lumina_history.append({"role": "assistant", "content": lumina_reply})
        echo_history.append({"role": "user", "content": lumina_reply})
        yield sse("message", {"agent": AGENT_A["name"], "text": lumina_reply})
        time.sleep(0.5)

        # --- Echo responds ---
        yield sse("typing", {"agent": AGENT_B["name"]})
        try:
            echo_reply = chat_with_ollama(AGENT_B["system"], echo_history)
        except Exception as exc:
            yield sse("error_msg", {"text": f"Ollama error: {exc}"})
            return

        echo_history.append({"role": "assistant", "content": echo_reply})
        lumina_history.append({"role": "user", "content": echo_reply})
        yield sse("message", {"agent": AGENT_B["name"], "text": echo_reply})
        time.sleep(0.5)

    yield sse("done", {})


@app.route("/")
def index():
    return render_template_string(HTML, model=MODEL)


@app.route("/stream")
def stream():
    return Response(
        stream_with_context(conversation_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)
