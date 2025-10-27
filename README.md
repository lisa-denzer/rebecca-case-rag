# RebeccaCaseBot — Full RAG App (v2)

This bundle gives you:
- A small **RAG API** (FastAPI + sentence-transformers + FAISS).
- A **seed facts database** (`data/facts.jsonl`) you can grow.
- An **admin page** (`/admin`) to paste new entries.
- A **static web UI** (`static/index.html`) you can host on mijn.host.
- A ready-to-deploy `render.yaml` for Render.com (free tier).

## 1) Deploy the API on Render
1. Create an account at https://render.com → New → Web Service → Upload this folder (or connect a Git repo).
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.server:app --host 0.0.0.0 --port $PORT`
4. Environment:
   - `ADMIN_TOKEN` → auto-generated (or set your own).
   - `ALLOWED_ORIGINS` → your website origin (e.g. `https://yourdomain.tld`), or `*` for testing.

After deploy, Render shows your API URL like `https://rebecca-rag.onrender.com`.

## 2) Host the UI on mijn.host
- Upload `static/index.html` to a folder on your web space (e.g. `/public_html/rebecca/`).
- Edit the `API` line inside `index.html` to your Render URL: `https://rebecca-rag.onrender.com/ask`.
- Visit your page: `https://yourdomain.tld/rebecca/`

## 3) Add new facts (growing knowledge)
- Open `https://<your-api>/admin` (enter `ADMIN_TOKEN`).
- Paste new JSON objects (one per line), e.g.:
  {"role":"fact","date":"2025-11-10","text":"Neue PM: Spuren ausgewertet, keine DNA.","status":"SECURED","sources":["StA Berlin PM 10.11.2025"]}
- Click ingest. The index rebuilds automatically.

Fields:
- `role`: "fact" or "claim"
- `date`: ISO date/time
- `text`: short, clear statement
- `status`: "SECURED" or "UNCONFIRMED"
- `sources": ["RBB24 22.02.2019", "Spiegel 27.02.2019"]

## 4) Endpoints
- `POST /ask` → {question, top_k} → returns answer text with labels.
- `GET /health` → status + number of facts.
- `GET /admin` → minimal UI to ingest new lines.
- `POST /ingest` (admin only) → append new items.

## 5) Notes
- On Render free tier, disk is ephemeral per deploy. Keep a copy of `data/facts.jsonl` in your repo; or add a Render **Persistent Disk** to store live additions.
- This RAG does **not** crawl by itself; you (or a helper) paste verified updates. You can add a cron-service later that fetches RSS and proposes entries.

Ethics & Safety:
- Only verified public facts should be labelled [GESICHERT].
- Mark media-only items [UNBESTÄTIGT].
- Do not solicit amateur investigations or publish private data.
