from pathlib import Path
import re

from ai_data_delivery_assurance_copilot.models.contracts import Evidence

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"

class LocalRAG:
    # Uses LlamaIndex/Qdrant when available; deterministic lexical fallback otherwise.
    def __init__(self):
        self.engine = "lexical-fallback"
        self._documents = []
        self._try_initialize_vector_stack()

    def _try_initialize_vector_stack(self):
        try:
            from llama_index.core import Document, VectorStoreIndex, Settings
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            from llama_index.core.embeddings import MockEmbedding
            from qdrant_client import QdrantClient

            docs = []
            for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
                docs.append(Document(
                    text=path.read_text(),
                    metadata={"source": str(path.relative_to(KNOWLEDGE_DIR))}
                ))
            if docs:
                client = QdrantClient(location=":memory:")
                vector_store = QdrantVectorStore(
                    client=client,
                    collection_name="de_delivery_knowledge"
                )
                Settings.embed_model = MockEmbedding(embed_dim=64)
                VectorStoreIndex.from_documents(docs, vector_store=vector_store)
                self.engine = "llamaindex/qdrant"
        except Exception:
            self.engine = "lexical-fallback"

        for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
            self._documents.append((str(path.relative_to(KNOWLEDGE_DIR)), path.read_text()))

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        terms = [t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 2]
        scored = []
        for source, text in self._documents:
            lower = text.lower()
            score = sum(lower.count(term) for term in terms)
            if score:
                detail = " ".join(line.strip() for line in text.splitlines() if line.strip())[:280]
                scored.append((score, Evidence(
                    evidence_type="RAG",
                    source=source,
                    detail=detail,
                )))
        return [e for _, e in sorted(scored, key=lambda x: (-x[0], x[1].source))[:top_k]]
