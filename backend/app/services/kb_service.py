import chromadb
import logging
from typing import Any

import httpx
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import Base_DIR, settings

logger = logging.getLogger(__name__)

KB_DIR = Base_DIR / "data" / "db"
CHROMA_DIR = Base_DIR / "data" / "kb"
COLLECTION_NAME = "library_kb"


_collection = None
_embedding_fn = None


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """使用本地 Ollama 的 embedding 接口生成向量"""

    def __init__(self, base_url: str | None = None, model_name: str | None = None):
        base_url = base_url or settings.OLLAMA_BASE_URL
        model_name = model_name or settings.OLLAMA_MODEL
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        texts = list(input)
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": texts},
            )
            response.raise_for_status()
            payload = response.json()

        embeddings = payload.get("embeddings") or []
        return [[float(value) for value in vector] for vector in embeddings]

    @staticmethod
    def name() -> str:
        return "ollama"

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    def get_config(self) -> dict[str, Any]:
        return {"base_url": self.base_url, "model_name": self.model_name}

    @classmethod
    def build_from_config(cls, config: dict[str, Any]) -> "OllamaEmbeddingFunction":
        return cls(
            base_url=config.get("base_url", settings.OLLAMA_BASE_URL),
            model_name=config.get("model_name", settings.OLLAMA_MODEL),
        )

    @staticmethod
    def validate_config(config: dict[str, Any]) -> None:
        return None


def _get_embedding_function():
    
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = OllamaEmbeddingFunction()
    return _embedding_fn


def get_collection():
    """初始化 ChromaDB 集合并导入 Markdown 知识文档"""
    global _collection
    if _collection is not None:
        return _collection

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_function(),
    )

    if col.count() == 0 and KB_DIR.exists():
        ids = []
        docs = []
        metas = []
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            try:
                col.add(ids=ids, documents=docs, metadatas=metas)
            except Exception:
                logger.exception("知识库文档写入向量库失败")
                raise

    _collection = col
    return col


def search(query: str, top_k: int = 3) -> str:
    """检索最相关的知识片段"""
    if not query or not query.strip():
        return ""

    col = get_collection()
    if col.count() == 0:
        return ""

    n_results = min(top_k, col.count())
    res = col.query(query_texts=[query], n_results=n_results)

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    score_parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        # 距离越小越相关；转换为 0-1 分数，越接近 1 越相关
        score = 1.0 / (1.0 + float(dist))
        if score < 0.5:
            continue
        source = meta.get("source") or "知识库"
        score_parts.append((score, f"[{source}]\n{doc}"))

    score_parts.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(item[1] for item in score_parts[:top_k])
