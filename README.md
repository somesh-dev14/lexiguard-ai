# LexiGuard AI

Locally running legal contract analysis with evidence-grounded question answering.

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS (`lexiguard-ai/frontend`)
- **Backend:** Python, FastAPI, PyMuPDF (`lexiguard-ai/backend`)
- **Clause classifier:** `litillabs/litil-clause-classifier` (ModernBERT-large fine-tuned on LEDGAR, 100 classes)
- **LLM:** Qwen3-4B via Ollama (`qwen3:4b`)
- **Experimental retrieval:** BM25 + all-MiniLM-L6-v2 + RRF + ms-marco cross-encoder (`QA_MODE=retrieval`)

Paper: `LexiGuard_AI_IEEE_Paper.pdf` (figures in `paper_figs/`).

## Not included in the repo (download separately)

| What | Where to put it | Source |
|---|---|---|
| Classifier weights `model.safetensors` (1.5 GB) | `LEDGAR_DeBERTa_Project/pretrained_model/` | https://huggingface.co/litillabs/litil-clause-classifier |
| Qwen3-4B | Ollama | `ollama pull qwen3:4b` |
| LegalBench-RAG, ContractNLI zips | `eval_downloads/` | see `lexiguard-ai/eval/README.md` |

## Run

```bash
# backend
cd lexiguard-ai/backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt   # plus requirements-evidence.txt for retrieval mode
copy ..\.env.example .env          # set AI_MODE=ai
python -m uvicorn app.main:app --port 8000

# frontend
cd lexiguard-ai/frontend
npm install && npm run dev        # http://localhost:5173
```

Tests: `pytest` in `backend`, `npx vitest run` in `frontend`.

*For informational purposes only; not legal advice.*
