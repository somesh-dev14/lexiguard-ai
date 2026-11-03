# LexiGuard AI

> A RAG LLM Framework for Intelligent Legal Document Summarization and Risk Analysis.

LexiGuard AI is an Apple-inspired legal technology web application that helps users understand lengthy legal contracts through structured summaries, clause analysis, risk identification, evidence-grounded Q&A, and downloadable reports.

---

## Architecture Overview

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Framer Motion.
- **Backend**: FastAPI, Pydantic v2, PyMuPDF (fitz) for PDF extraction.
- **AI Mode**: Transparent deterministic Demo Mode with support for local embeddings / DeBERTa / LLM integration.

---

## Quickstart Guide

### 1. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Backend health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. Frontend Setup (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Core Features
1. **Executive Summary**: Overview of parties, effective dates, durations, and obligations.
2. **Clause Analysis**: Categorization of clauses with source page tracking and explanations.
3. **Risk Analysis**: Severity-rated (Critical, High, Medium, Low) liability analysis with cited excerpts.
4. **Interactive Q&A**: Question-answering interface grounded in contract text with page citations.
5. **Source Document Explorer**: Full page-by-page extracted text viewer with copy and search capabilities.

---

*Disclaimer: LexiGuard AI is designed for informational and document analysis orientation purposes only and does not constitute formal legal advice.*
