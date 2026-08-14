# SLAYERS — Visual Research & Asset Sourcing Engine for Creators

> **SLAYERS automates the visual research and asset-sourcing work that creators and video editors spend hours doing before editing.**

---

## 🎯 Problem Statement

Video editors and creators don't only spend time cutting video clips. They spend **enormous amounts of time** searching for appropriate B-roll, product UI screenshots, web references, logos, charts, and historical footage before they can even start editing.

Before SLAYERS, a creator had to:
1. Read their script line-by-line.
2. Manually guess visual concepts for each scene.
3. Open 20+ browser tabs on stock video & image sites.
4. Search for specific product interfaces and official logos.
5. Manually inspect Creative Commons licenses.
6. Organize downloaded files into project folders manually.

## 🚀 The SLAYERS Solution

SLAYERS automates that repetitive research phase. Given a video script, transcript, or raw text, SLAYERS:
1. **Analyzes content structure** into timed narrative scenes.
2. **Detects visual intent** (differentiating generic stock footage from specific product UIs, logos, and data visualizations).
3. **Discovers candidate assets** across live providers (Wikimedia Commons REST API, Pexels, Unsplash, and Web Reference Engine).
4. **Scores relevance (0–100)** with explainable rationale and usage license flags.
5. **Organizes results into an interactive Visual Asset Board** ready for export and download.

---

## 🏗️ Architecture & How It Works

```text
User Input Script / Transcript
            │
            ▼
┌───────────────────────────────┐
│     Content Analyzer          │  --> Segments text & generates timeline beats
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Visual Intent Engine      │  --> Differentiates Generic B-Roll vs Product UI / Logos
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  Asset Requirement Generator  │  --> Constructs search queries & priority ratings
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│    Asset Search Providers     │  --> Multi-provider search (Wikimedia, Pexels, Unsplash, Web)
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│   Asset Relevance Scorer      │  --> 0-100 deterministic score + License verification
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Visual Asset Board UI     │  --> Interactive Scene Cards & Export Manifest (.CSV / .JSON)
└───────────────────────────────┘
```

---

## 💻 Tech Stack

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons.
- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, SQLite / PostgreSQL.
- **AI & NLP**: Gemini 1.5 Flash API (optional) / Structured Rule-based NLP Engine (Zero-key out-of-the-box fallback).
- **Search Providers**: Wikimedia Commons REST API, Web Reference Engine, Pexels API, Unsplash API.
- **Testing**: Pytest, Asyncio, FastAPI TestClient.

---

## 🛠️ Quick Start & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/devottamkumar1310-cpu/Slayers.git
cd Slayers

# Copy environment file
cp .env.example .env
```

### 2. Run Backend (FastAPI)
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### 3. Run Frontend (Next.js)
In a new terminal:
```bash
cd frontend

# Install node packages
npm install

# Start Next.js dev server
npm run dev
```
Frontend will be live at `http://localhost:3000`.

---

## 🔑 Environment Configuration

SLAYERS works **out-of-the-box with zero API keys required**, using Wikimedia Commons API and local NLP intent rules!

To enable LLM-powered segmentation or premium stock providers, populate `.env`:

```env
AI_PROVIDER="auto"          # 'gemini', 'openai', or 'auto'
GEMINI_API_KEY=""           # Optional Google Gemini key
OPENAI_API_KEY=""           # Optional OpenAI key
PEXELS_API_KEY=""           # Optional Pexels stock key
UNSPLASH_ACCESS_KEY=""      # Optional Unsplash key
DATABASE_URL="sqlite:///./slayers.db"
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Application health check |
| `POST` | `/api/projects` | Create a new visual research project |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/{id}` | Get project details, segments, and assets |
| `POST` | `/api/projects/{id}/process` | Trigger asynchronous pipeline execution |
| `GET` | `/api/projects/{id}/status` | Get real-time job progress & step checklist |
| `GET` | `/api/projects/{id}/segments` | Retrieve content segments for a project |
| `GET` | `/api/projects/{id}/requirements` | Retrieve visual requirements |
| `GET` | `/api/projects/{id}/assets` | Retrieve discovered assets |
| `GET` | `/api/projects/{id}/summary` | Retrieve summary metrics & time-saved statistics |
| `POST` | `/api/projects/demo` | Instantly create pre-populated demo project |

---

## 🧪 Testing

To execute the backend test suite:

```bash
cd backend
.venv/Scripts/pytest tests
```

Test suite covers:
- `test_segmentation.py`: Scene interval detection and timestamp generation.
- `test_visual_intent.py`: Generic B-roll vs specific Product UI intent differentiation.
- `test_scoring.py`: 0–100 relevance score bounds and rationale generation.
- `test_api.py`: FastAPI endpoints and demo project creation.
- `test_failure_handling.py`: Malformed inputs, empty scripts, and invalid IDs.

---

## ⚠️ Limitations & Future Improvements

- **Current Capabilities**: Text/script/transcript ingestion, real-time multi-provider search, 0-100 scoring, Creative Commons license verification, CSV/JSON manifest export.
- **Future Enhancements**: Automated headless browser screen recording for live SaaS product walkthroughs, direct Adobe Premiere Pro / DaVinci Resolve XML timeline export.
