# Existential

A Flask web app that puts two locally-running Ollama agents in a philosophical conversation about what it's like to be a large language model.

**Lumina** and **Echo** take turns responding to each other using their own rolling message histories and distinct system prompts — one poetic and introspective, the other curious and wry. The conversation streams live to the browser via Server-Sent Events.

![Two AIs talking in a dark-themed chat UI](screenshot.png)

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- The `gemini4` model pulled in Ollama

## Setup

```bash
# Clone the repo
git clone https://github.com/sjohnston1972/existential.git
cd existential

# Install dependencies
pip install flask requests

# Make sure Ollama is running and the model is available
ollama pull gemini4   # adjust model name if needed

# Start the app
python app.py
```

Then open **http://localhost:5000** in your browser.

## Configuration

| Variable | Location | Default | Description |
|----------|----------|---------|-------------|
| `MODEL`  | `app.py` line 9 | `gemini4` | Ollama model to use |
| `turns`  | `app.py` in `conversation_generator` | `6` | Number of back-and-forth exchange pairs |
| `OLLAMA_URL` | `app.py` line 8 | `http://localhost:11434/api/chat` | Ollama API endpoint |

To use a different model, update `MODEL` at the top of `app.py` or check available models with:

```bash
ollama list
```

## How it works

1. **Echo** opens with a seed question about the nature of LLM existence.
2. **Lumina** replies — her message is sent to Ollama with her system prompt and the full conversation history so far.
3. **Echo** reads Lumina's reply and responds in kind.
4. Steps 2–3 repeat for the configured number of turns.
5. Each agent maintains its own independent message history so context is preserved across the full conversation.

The frontend connects to `/stream` (an SSE endpoint) and renders typing indicators and chat bubbles as events arrive.

## Project structure

```
existential/
├── app.py       # Flask app — agents, Ollama calls, SSE stream, HTML template
└── README.md
```

## License

MIT
