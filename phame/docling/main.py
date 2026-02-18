# pip install docling pydantic httpx numpy
import os, asyncio, numpy as np
from typing import List, Dict, Tuple
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
import httpx

# ---------- 1) Config ----------
class Settings(BaseSettings):
    PORTKEY_API_KEY: str
    PORTKEY_BASE_URL: str = os.environ.get("PORTKEY_BASE_URL")
    PORTKEY_VIRTUAL_KEY: str | None = None  # preferred
    PORTKEY_PROVIDER: str | None = "@opal"  # or None if using virtual key
    CHAT_MODEL: str = "@opal/openai/gpt-oss-120b"
    EMBED_MODEL: str = "@opal/intfloat/e5-large-v2"
    class Config: env_file = ".env"

cfg = Settings()

# ---------- 2) Portkey client (async) ----------
def _pk_headers():
    kw = {"api_key": cfg.PORTKEY_API_KEY}
    if cfg.PORTKEY_VIRTUAL_KEY: kw["virtual_key"] = cfg.PORTKEY_VIRTUAL_KEY
    elif cfg.PORTKEY_PROVIDER:  kw["provider"] = cfg.PORTKEY_PROVIDER
    return createHeaders(**kw, metadata={"app":"docling-rag"})

class Portkey:
    def __init__(self):
        self.h = _pk_headers()
        self.client = httpx.AsyncClient(timeout=60)

    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        payload = {"model": model, "input": texts}
        r = await self.client.post(f"{cfg.PORTKEY_BASE_URL}/embeddings", headers=self.h, json=payload)
        r.raise_for_status()
        data = r.json()
        return [d["embedding"] for d in data["data"]]

    async def chat(self, messages: List[Dict], model: str) -> str:
        payload = {"model": model, "messages": messages, "temperature": 0.2}
        r = await self.client.post(f"{cfg.PORTKEY_BASE_URL}/chat/completions", headers=self.h, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    async def aclose(self): await self.client.aclose()

# ---------- 3) Docling convert + chunk ----------
from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker  # native chunker over DoclingDocument

async def docling_to_chunks(source: str) -> List[Dict]:
    """
    Returns a list of chunk dicts: {"id", "text", "meta"} using Docling’s native chunker.
    """
    converter = DocumentConverter()        # sensible defaults; supports URLs and paths
    doc = converter.convert(source).document   # -> DoclingDocument (Pydantic) :contentReference[oaicite:2]{index=2}

    # Use structural chunking that respects headings/tables/captions, etc. :contentReference[oaicite:3]{index=3}
    chunker = HierarchicalChunker()
    chunks = []
    for i, ch in enumerate(chunker.chunk(doc)):
        # Each "ch" contains text + rich metadata assembled from DoclingDocument
        text = ch.text
        meta = ch.metadata or {}
        chunks.append({"id": f"{os.path.basename(source)}#{i}", "text": text, "meta": meta})
    return chunks

# ---------- 4) Tiny in-memory index (cosine) ----------
class MemIndex:
    def __init__(self):
        self.ids: List[str] = []
        self.meta: List[Dict] = []
        self.vecs: np.ndarray | None = None

    def upsert(self, rows: List[Tuple[str, Dict, List[float]]]):
        vecs = np.array([v for _,_,v in rows], dtype="float32")
        if self.vecs is None:
            self.vecs = vecs
            self.ids  = [rid for rid,_,_ in rows]
            self.meta = [m for _,m,_ in rows]
        else:
            self.vecs = np.vstack([self.vecs, vecs])
            self.ids.extend([rid for rid,_,_ in rows])
            self.meta.extend([m for _,m,_ in rows])

    def search(self, q: List[float], k=5):
        if self.vecs is None or len(self.ids)==0: return []
        A = self.vecs / (np.linalg.norm(self.vecs, axis=1, keepdims=True)+1e-12)
        b = np.array(q, dtype="float32"); b = b/(np.linalg.norm(b)+1e-12)
        sims = A @ b
        idx = np.argsort(-sims)[:k]
        return [(self.ids[i], self.meta[i], float(sims[i])) for i in idx]

# ---------- 5) Build & query ----------
async def build_index(sources: List[str]) -> Tuple[MemIndex, Portkey]:
    pk = Portkey()
    idx = MemIndex()
    for src in sources:
        chunks = await docling_to_chunks(src)
        texts = [c["text"] for c in chunks]
        vecs  = await pk.embed(texts, model=cfg.EMBED_MODEL)
        rows  = [(c["id"], c["meta"], v) for c,v in zip(chunks, vecs)]
        idx.upsert(rows)
    return idx, pk

async def ask(query: str, idx: MemIndex, pk: Portkey, k=5):
    qvec = (await pk.embed([query], model=cfg.EMBED_MODEL))[0]
    top = idx.search(qvec, k=k)
    context = "\n\n---\n\n".join([f"[{rid}] {m.get('title','')}\n{m.get('text','') or ''}".strip() for rid,m,_ in top])
    messages = [
        {"role":"system","content":"Answer using the provided context. If unsure, say you don't know."},
        {"role":"user","content":f"Question: {query}\n\nContext:\n{context}"}
    ]
    answer = await pk.chat(messages, model=cfg.CHAT_MODEL)
    return answer, top

async def main():
    # Example: any PDF/URL supported by Docling
    # sources = ["https://arxiv.org/pdf/2408.09869"]  # swap with your docs
    sources = [
        "/home/amundrj1/phame/input_data/pdfs/Shingleys_Chapters/Shigley_Chapter16.pdf"
    ]
    idx, pk = await build_index(sources)
    try:
        ans, top = await ask("Summarize the main contribution.", idx, pk, k=5)
        print("\n=== ANSWER ===\n", ans)
        print("\n=== SOURCES ===")
        for rid, meta, score in top:
            print(f"{rid}  score={score:.3f}  meta_keys={list(meta.keys())[:5]}")
    finally:
        await pk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
