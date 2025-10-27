import os, json
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "facts.jsonl")

MODEL_NAME = os.environ.get("EMBED_MODEL","sentence-transformers/all-MiniLM-L6-v2")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN","change-me")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS","*").split(",")

app = FastAPI(title="RebeccaCaseBot RAG API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS!=["*"] else ["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class AskReq(BaseModel):
    question: str
    top_k: int = 6

class IngestReq(BaseModel):
    items: List[Dict]

def load_facts() -> List[Dict]:
    facts = []
    if not os.path.exists(DATA_PATH):
        return facts
    with open(DATA_PATH,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: facts.append(json.loads(line))
            except: pass
    return facts

FACTS: List[Dict] = load_facts()

def build_index(facts: List[Dict]):
    model = SentenceTransformer(MODEL_NAME)
    texts = [f"{x.get('status','')} | {x.get('date','')} | {x.get('text','')}" for x in facts]
    if not texts:
        embs = np.zeros((0,384), dtype='float32')
        index = faiss.IndexFlatIP(384)
        return index, embs, model
    embs = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    index = faiss.IndexFlatIP(embs.shape[1]); index.add(embs)
    return index, embs, model

INDEX, EMBEDDINGS, MODEL = build_index(FACTS)

def retrieve(query: str, top_k:int=6):
    if len(FACTS)==0: return []
    q = MODEL.encode([query], normalize_embeddings=True, convert_to_numpy=True)
    D, I = INDEX.search(q, min(top_k, len(FACTS)))
    hits=[]; 
    for score, idx in zip(D[0], I[0]):
        item = FACTS[int(idx)]
        hits.append({"score": float(score), "item": item})
    return hits

def compose_answer(hits: List[Dict]) -> str:
    if not hits: return "Keine Daten im Index. Bitte später erneut versuchen."
    secured = [h for h in hits if h['item'].get('status')=='SECURED']
    unconf  = [h for h in hits if h['item'].get('status')=='UNCONFIRMED']
    out=[]
    if secured:
        out.append("[GESICHERT]")
        for h in secured:
            it=h['item']; src="; ".join(it.get('sources', []))
            out.append(f"– ({it.get('date')}) {it.get('text')} — Quellen: {src}")
    if unconf:
        out.append("\n[UNBESTÄTIGT]")
        for h in unconf:
            it=h['item']; src="; ".join(it.get('sources', []))
            out.append(f"– ({it.get('date')}) {it.get('text')} — Quellen: {src}")
    return "\n".join(out)

def require_admin(req: Request):
    token = req.headers.get("X-Admin-Token") or req.query_params.get("token")
    if not token or token != ADMIN_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/health")
def health(): return {"ok": True, "facts": len(FACTS)}

@app.post("/ask")
def ask(req: AskReq):
    hits = retrieve(req.question, req.top_k)
    return {"answer": compose_answer(hits), "count": len(hits)}

@app.post("/ingest")
def ingest(data: IngestReq, _: bool = Depends(require_admin)):
    added=0
    with open(DATA_PATH,"a",encoding="utf-8") as f:
        for it in data.items:
            f.write(json.dumps(it, ensure_ascii=False)+"\n"); added+=1
    global FACTS, INDEX, EMBEDDINGS, MODEL
    FACTS = load_facts()
    INDEX, EMBEDDINGS, MODEL = build_index(FACTS)
    return {"added": added, "total": len(FACTS)}

ADMIN_HTML = """<!doctype html><meta charset="utf-8">
<title>RebeccaCaseBot Admin</title>
<style>body{font-family:system-ui;margin:2rem;max-width:800px}</style>
<h1>Admin – neue Einträge</h1>
<p>Felder: role, date, text, status (SECURED/UNCONFIRMED), sources [..]</p>
<textarea id="ta" rows="12" style="width:100%"></textarea><br>
<input id="tok" placeholder="Admin Token" style="width:50%"><button onclick="send()">Ingest</button>
<pre id="out"></pre>
<script>
async function send(){
  const lines = document.getElementById('ta').value.split('\\n').map(s=>s.trim()).filter(Boolean);
  const items = lines.map(l=>JSON.parse(l));
  const r = await fetch('/ingest',{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':document.getElementById('tok').value},body:JSON.stringify({items})});
  const j = await r.json(); document.getElementById('out').textContent = JSON.stringify(j,null,2);
}
</script>
"""
@app.get("/admin", response_class=HTMLResponse)
def admin(_: Request): return HTMLResponse(ADMIN_HTML)
