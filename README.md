# DiaIntel — Pharmacovigilance Intelligence Platform

> AI-powered drug safety monitoring for Type 2 Diabetes medications.
> Built for HackCrux 2026 @ LNMIIT.

## 🎯 Overview

DiaIntel is an end-to-end NLP pharmacovigilance platform that:
- Loads real Reddit posts from Pushshift `.zst` dump files
- Extracts drug names and dosages using custom NER + RxNorm lexicon
- Extracts adverse events using BioBERT (batch) and DistilBERT (real-time)
- Scores sentiment per drug using RoBERTa
- Flags medical misinformation using zero-shot classification (BART-MNLI)
- Builds a Drug–Adverse Event knowledge graph using NetworkX
- Stores everything in PostgreSQL + TimescaleDB
- Exposes a FastAPI backend with WebSocket support
- Displays results on a React + TailwindCSS + D3.js dashboard

## 💊 Target Drugs

| Drug | Generic Name | Class |
|------|-------------|-------|
| Metformin | metformin | Biguanide |
| Ozempic | semaglutide | GLP-1 RA |
| Jardiance | empagliflozin | SGLT2 Inhibitor |
| Januvia | sitagliptin | DPP-4 Inhibitor |
| Farxiga | dapagliflozin | SGLT2 Inhibitor |
| Trulicity | dulaglutide | GLP-1 RA |
| Victoza | liraglutide | GLP-1 RA |
| Glipizide | glipizide | Sulfonylurea |

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows/Mac/Linux)
- `.zst` data files in `backend/data/raw/`

### 1. Download ML Models (First Time Only)

> ⚠️ This downloads ~5GB of models. Takes 10-15 minutes on a good connection.

```powershell
cd backend
pip install transformers torch
python scripts/download_models.py
```

### 2. Start the Stack

```powershell
docker compose up --build
```

### 3. Open the Dashboard

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│  PostgreSQL  │
│  React/Vite  │     │   FastAPI   │     │ TimescaleDB  │
│  Port 5173   │◀────│  Port 8000  │     │  Port 5432   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    │  Port 6379  │
                    └─────────────┘
```

## 📁 Project Structure

```
diaintel/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Environment config
│   │   ├── database.py       # SQLAlchemy setup
│   │   ├── models/           # ORM + Pydantic schemas
│   │   ├── api/              # REST routes + WebSocket
│   │   ├── nlp/              # NLP pipeline modules
│   │   ├── ingestion/        # Pushshift data loader
│   │   └── utils/            # RxNorm, MedDRA mappers
│   ├── data/raw/             # .zst dump files
│   ├── db/init.sql           # Database schema
│   └── scripts/              # Model download + seed data
├── frontend/
│   ├── src/
│   │   ├── pages/            # 6 page components
│   │   ├── components/       # Reusable UI components
│   │   ├── services/         # API + WebSocket clients
│   │   └── hooks/            # Custom React hooks
│   └── package.json
└── docker-compose.yml
```

## 🔧 Verification Commands

After `docker compose up`, verify everything is healthy:

```powershell
# Check all services are running
docker compose ps

# Verify PostgreSQL tables
docker compose exec postgres psql -U diaintel -d diaintel -c "\dt"

# Verify Redis
docker compose exec redis redis-cli ping

# Check backend health
Invoke-RestMethod http://localhost:8000/health

# Check frontend
Start-Process http://localhost:5173
```

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TailwindCSS, Recharts, D3.js |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| NLP | BioBERT, DistilBERT, RoBERTa, BART-MNLI, spaCy |
| Database | PostgreSQL 15 + TimescaleDB |
| Cache | Redis 7 |
| Graph | NetworkX |
| Infrastructure | Docker, Docker Compose |

## 📜 License

Built for HackCrux 2026 at LNMIIT.
