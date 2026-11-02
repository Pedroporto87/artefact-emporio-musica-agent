"""Home page da loja: catálogo por categoria + chat com a Marina (FastAPI).

Uso: python src/web.py  ->  http://127.0.0.1:8000
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))

from agent import MusicaAgent
from data_loader import DataLoader
from tools.policies import store_status

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).parent / "static"
MAX_SESSIONS = 200
MAX_CARDS = 6

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("LLM_API_KEY")

loader = DataLoader()
loader.load_all()
# Uma instância do agente por visitante: o histórico multi-turno fica em memória.
sessions: Dict[str, MusicaAgent] = {}

app = FastAPI(title="Empório da Música")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: Optional[str] = None


def product_card(product_id: int) -> Dict:
    p = loader.get_product_with_promotion(product_id)
    promo = p["promotion"]
    return {
        "product_id": int(p["product_id"]),
        "name": p["name"],
        "category_id": int(p["category_id"]),
        "category": loader.get_category_name(int(p["category_id"])),
        "price_brl": float(p["price_brl"]),
        "pix_price": p["pix_price"],
        "stock_quantity": int(p["stock_quantity"]),
        "description": p["description"],
        "specs": p.get("specs") or {},
        "promotion": promo and {
            "name": promo["name"],
            "discount_percent": float(promo["discount_percent"]),
            "discounted_price": float(promo["discounted_price"]),
        },
    }


def mentioned_products(reply: str, candidate_ids: List[int]) -> List[int]:
    """Dos produtos que as ferramentas devolveram, quais a Marina citou na resposta."""
    text = DataLoader._normalize_text(reply).replace("-", "")
    names = loader.products.set_index("product_id")["name_normalized"]
    hits = []
    for pid in candidate_ids:
        words = names[pid].replace("-", "").split()
        model = next((w for w in words if any(c.isdigit() for c in w)), None)
        if " ".join(words) in text or (words[0] in text and model and model in text):
            hits.append(pid)
    if hits:
        return hits[:MAX_CARDS]
    return candidate_ids if len(candidate_ids) <= MAX_CARDS else []


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/catalog")
def catalog():
    products = [product_card(int(pid)) for pid in loader.products.sort_values("price_brl")["product_id"]]
    counts: Dict[int, int] = {}
    for p in products:
        counts[p["category_id"]] = counts.get(p["category_id"], 0) + 1
    categories = [
        {"category_id": int(row["category_id"]), "name": row["name"], "product_count": counts[int(row["category_id"])]}
        for _, row in loader.categories.iterrows()
        if int(row["category_id"]) in counts
    ]
    return {"categories": categories, "products": products, "store": store_status()}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not API_KEY:
        raise HTTPException(503, "LLM_API_KEY não configurada no .env")
    session_id = req.session_id if req.session_id in sessions else str(uuid.uuid4())
    if session_id not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))
        sessions[session_id] = MusicaAgent(API_KEY, loader=loader)
    agent = sessions[session_id]
    try:
        reply = agent.process_message(req.message)
    except Exception as exc:
        print(f"[erro no chat] {exc!r}")
        raise HTTPException(502, "A Marina não conseguiu responder agora. Tente de novo em instantes.")
    ids = mentioned_products(reply, agent.last_product_ids)
    return {"session_id": session_id, "reply": reply, "products": [product_card(i) for i in ids]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
