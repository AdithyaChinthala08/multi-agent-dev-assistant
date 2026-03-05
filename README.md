# ⟁ AgentForge — Multi-Agent Dev Assistant

> A production-grade AI pipeline that takes a plain English description and generates code, tests, and a code review — all streamed live to your browser.

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/multi-agent-dev-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/multi-agent-dev-assistant/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?logo=react)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1-purple)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## 🎬 Demo

![Demo GIF](docs/demo.gif)

**Live URL:** https://your-render-url.onrender.com

---

## 🏗️ Architecture

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│   (WebSocket client — streams agent output live)        │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket / REST
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  POST /api/sessions ──► Create session in PostgreSQL     │
│  WS   /api/ws/{id}  ──► Stream agent pipeline output    │
│  GET  /api/sessions ──► List session history             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Multi-Agent Pipeline              │
│                                                          │
│  ┌────────────────┐                                      │
│  │  Agent 1       │  ──► Generates Python code           │
│  │  Code Generator│      (LLaMA3-70b via Groq)           │
│  └───────┬────────┘                                      │
│          │                                               │
│          ▼                                               │
│  ┌────────────────┐                                      │
│  │  Agent 2       │  ──► Writes pytest unit tests        │
│  │  Test Writer   │      for the generated code          │
│  └───────┬────────┘                                      │
│          │                                               │
│          ▼                                               │
│  ┌────────────────┐                                      │
│  │  Agent 3       │  ──► Reviews code + tests            │
│  │  Code Reviewer │      gives quality score & feedback  │
│  └────────────────┘                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │  ──► Persists sessions
              │   (sessions +   │       & agent outputs
              │    agent runs)  │
              └─────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Agents** | LangGraph + LangChain |
| **LLM** | Groq API — LLaMA3-70b (free) |
| **Backend** | FastAPI + Python 3.11 |
| **Real-time** | WebSockets (native FastAPI) |
| **Database** | PostgreSQL + SQLAlchemy (async) |
| **Frontend** | React 18 |
| **Containerization** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |
| **Deployment** | Render |

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/multi-agent-dev-assistant.git
cd multi-agent-dev-assistant
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=gsk_your_key_here
```

### 2. Run with Docker

```bash
docker-compose up --build
```

### 3. Open the app

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health

---

## 💻 Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set env vars
export GROQ_API_KEY=gsk_your_key_here
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agentdb

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

---

## 📡 API Reference

### `POST /api/sessions`
Create a new agent session.
```json
{ "prompt": "Write a binary search function" }
```
Returns: `{ "session_id": "uuid", "status": "pending" }`

### `WS /api/ws/{session_id}`
Stream agent pipeline. Send `{ "prompt": "..." }` after connecting.

Event types streamed:
```
{ "type": "agent_start",        "agent": "Code Generator", "order": 1 }
{ "type": "agent_chunk",        "agent": "Code Generator", "chunk": "def ..." }
{ "type": "agent_done",         "agent": "Code Generator", "output": "..." }
{ "type": "pipeline_complete" }
{ "type": "error",              "message": "..." }
```

### `GET /api/sessions`
List recent sessions.

### `GET /api/sessions/{id}`
Get session with full agent outputs.

---

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🌐 Deploy to Render

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Set environment variables (GROQ_API_KEY, DATABASE_URL)
5. Build command: `docker-compose up --build`

---

## 📁 Project Structure

```
multi-agent-dev-assistant/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── pipeline.py      # LangGraph pipeline definition
│   │   │   ├── runner.py        # Streaming agent execution
│   │   │   └── streaming.py     # WebSocket connection manager
│   │   ├── api/
│   │   │   └── routes.py        # FastAPI routes + WebSocket
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   └── database.py      # Async SQLAlchemy setup
│   │   ├── models/
│   │   │   └── session.py       # DB models
│   │   └── main.py              # FastAPI app entry point
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js               # Main React dashboard
│   │   └── App.css              # Terminal aesthetic styles
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI/CD
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🤝 Contributing

PRs welcome! Please open an issue first.

---

## 📄 License

MIT
