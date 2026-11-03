from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "LexiGuard AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    AI_MODE: str = "demo"  # "demo" or "ai"
    MAX_FILE_SIZE_MB: int = 50

    # Local Pretrained Classifier Settings
    MODEL_DIR: str = str((Path(__file__).resolve().parents[4] / "LEDGAR_DeBERTa_Project" / "pretrained_model").resolve())
    CLASSIFIER_SRC_DIR: str = str((Path(__file__).resolve().parents[4] / "LEDGAR_DeBERTa_Project" / "src").resolve())
    CLASSIFIER_TOP_K: int = 3

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_NUM_PREDICT: int = 512
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_DISABLE_THINKING: bool = True

    # Chat Q&A mode (experimental evidence-retrieval extension)
    # "baseline"  = original behaviour: all pages in the prompt (default)
    # "retrieval" = B1: one-shot hybrid clause retrieval (BM25 + dense + rerank)
    QA_MODE: str = "baseline"

    # Evidence index / retrieval settings
    EVIDENCE_MAX_CLAUSES: int = 500
    # Longer clauses are split into windows (MiniLM reads ~256 tokens, the reranker ~512); 0 = no cap
    EVIDENCE_MAX_CLAUSE_CHARS: int = 1500
    EVIDENCE_TOP_K: int = 5
    EVIDENCE_CANDIDATE_POOL: int = 20
    EVIDENCE_RRF_K: int = 60
    EVIDENCE_MAX_CONTEXT_CHARS: int = 12000
    EVIDENCE_DENSE_ENABLED: bool = True
    EVIDENCE_RERANK_ENABLED: bool = True
    EVIDENCE_EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EVIDENCE_RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    EVIDENCE_MODELS_LOCAL_ONLY: bool = True
    EVIDENCE_CLASSIFY_AT_INDEX: bool = False
    # torch / sentence-transformers / faiss live in the system Python, not the venv
    ML_SITE_PACKAGES: str = r"C:\Users\warso\AppData\Local\Programs\Python\Python312\Lib\site-packages"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
