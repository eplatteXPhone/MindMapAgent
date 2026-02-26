# MindMapAgent

Collaborative brainstorming web app with AI-powered mindmap generation.

A moderator creates a session, participants join via session code, everyone submits ideas in real-time, and Claude analyses all ideas — deduplicating, categorising, detecting dependencies — then generates an interactive HTML mindmap.

## Tech Stack

- **Flet** — Python UI framework with built-in real-time pub/sub
- **Claude API** — Idea analysis via `anthropic` SDK (Sonnet 4.6)
- **markmap** — Interactive mindmap rendering from markdown
- **UV** — Python package management

## Setup

```bash
cd /Users/qa/Playground/MindMapAgent

# Install dependencies
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Run

```bash
uv run flet run main.py --web --port 8000
```

Open `http://localhost:8000` in your browser.

To share with others on the same network: `http://<your-local-ip>:8000`

For external access: `ngrok http 8000`

## How It Works

1. **Create a session** — Enter a brainstorming topic
2. **Share the code** — Give participants the 6-character session code
3. **Brainstorm** — Everyone submits ideas in real-time
4. **Generate** — Moderator clicks "Generate Mindmap"
5. **View** — Claude analyses ideas and produces an interactive mindmap

The generated mindmap HTML is saved to `output/` and can be opened standalone in any browser.

## Project Structure

```
main.py                 # Flet app entry point (UI + routing)
session.py              # Session/Idea models + in-memory store
llm.py                  # Claude API integration
mindmap.py              # JSON → markdown → HTML conversion
mindmap_template.html   # Jinja2 template with markmap-autoloader
output/                 # Generated mindmap HTML files
```
