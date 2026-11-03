"""
LexiGuard evidence-retrieval evaluation harness.

Part 1 (always, no LLM needed):
  - retrieval metrics for B1 variants: bm25, dense, hybrid, hybrid+rerank
  - baseline context coverage: is each gold evidence text present in the prompt
    the original full-document mode builds (after its 3,000-char page cut)?

Part 2 (--with-llm, needs Ollama running):
  - runs the real chat function in "baseline" and "retrieval" modes
  - records answers, citations, latency, heuristic abstention flags
  - writes grading.csv for manual correctness grading

Usage (from lexiguard-ai/backend, with the app venv):
  venv\\Scripts\\python.exe ..\\eval\\run_eval.py
  venv\\Scripts\\python.exe ..\\eval\\run_eval.py --with-llm
  venv\\Scripts\\python.exe ..\\eval\\run_eval.py --data ..\\eval\\data\\seed --variants bm25,hybrid+rerank

Nothing here reports results the run did not measure. Summaries are
descriptive; with a small dataset they are not evidence of an effect.
"""

import argparse
import asyncio
import csv
import json
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent / "backend"

VARIANTS = {
    "bm25": dict(use_bm25=True, use_dense=False, use_rerank=False),
    "dense": dict(use_bm25=False, use_dense=True, use_rerank=False),
    "hybrid": dict(use_bm25=True, use_dense=True, use_rerank=False),
    "hybrid+rerank": dict(use_bm25=True, use_dense=True, use_rerank=True),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(EVAL_DIR / "data" / "seed"), help="dataset directory")
    p.add_argument("--out", default=str(EVAL_DIR / "results"), help="results root directory")
    p.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated retrieval variants")
    p.add_argument("--ks", default="1,3,5,10", help="cut-offs for retrieval metrics")
    p.add_argument("--with-llm", action="store_true", help="also run the chat pipeline through Ollama")
    p.add_argument("--qa-modes", default="baseline,retrieval", help="chat modes for --with-llm")
    p.add_argument("--assumed-num-ctx", type=int, default=None,
                   help="optional: context window (tokens) to compare baseline prompt size against")
    p.add_argument("--limit", type=int, default=None, help="only the first N questions (debugging)")
    p.add_argument("--budgets", default="4000,8000,12000",
                   help="character budgets: clauses are added in rank order while they fit, as the app's "
                        "format_context does (EVIDENCE_MAX_CONTEXT_CHARS = 12000); '' disables")
    p.add_argument("--budget-pool", type=int, default=60, help="candidates retrieved for the budget metrics")
    p.add_argument("--span-threshold", type=float, default=0.5,
                   help="share of a gold span the top-k clauses must cover to count as retrieved")
    return p.parse_args()


def main():
    args = parse_args()
    data_dir = Path(args.data).resolve()
    out_root = Path(args.out).resolve()
    ks = [int(k) for k in args.ks.split(",")]
    budgets = [int(b) for b in args.budgets.split(",") if b.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in VARIANTS:
            sys.exit(f"Unknown variant '{v}'. Choose from: {', '.join(VARIANTS)}")

    # Import the app the same way the server sees it (.env is read from backend/)
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))
    sys.path.insert(0, str(EVAL_DIR))

    from app.core.config import settings
    from app.services.chat_service import _build_page_context
    from app.services.evidence.index import build_evidence_index
    from app.services.evidence.retriever import retrieve
    from app.services.evidence import dense as dense_mod
    import dataset as ds
    import metrics as m

    meta = ds.load_meta(data_dir)
    questions = ds.load_questions(data_dir / "questions.jsonl")
    if args.limit:
        questions = questions[: args.limit]
    contract_names = sorted({q.contract for q in questions})
    docs = {name: ds.load_contract(data_dir / "contracts" / name) for name in contract_names if (data_dir / "contracts" / name).exists()}

    problems = ds.resolve_spans(questions, docs)
    for pr in problems:
        print("DATASET WARNING:", pr)

    need_dense = any(VARIANTS[v]["use_dense"] for v in variants) or args.with_llm
    print(f"Indexing {len(docs)} contract(s){' with dense embeddings (first load can take ~1 min)' if need_dense else ''}...")
    indexes = {}
    for i, (name, doc) in enumerate(docs.items(), 1):
        indexes[name] = build_evidence_index(doc, with_dense=need_dense)
        if len(docs) > 5 and i % 5 == 0:
            print(f"  indexed {i}/{len(docs)}")
    seg_warnings = ds.segmentation_warnings(questions, indexes)
    if seg_warnings:
        print(f"Note: {len(seg_warnings)} gold span(s) cross a clause boundary (see config.json)")

    run_dir = out_root / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "data": str(data_dir),
        "dataset_meta": meta,
        "setting": "within-document retrieval: each question searches only the clauses of its own contract",
        "span_threshold": args.span_threshold,
        "questions": len(questions),
        "contracts": {n: {"pages": d.page_count, "words": d.word_count, "index": indexes[n].summary()} for n, d in docs.items()},
        "variants": variants,
        "ks": ks,
        "with_llm": args.with_llm,
        "settings": {k: getattr(settings, k) for k in dir(settings) if k.startswith(("EVIDENCE_", "OLLAMA_", "QA_MODE"))},
        "model_load_errors": dense_mod.load_errors(),
        "dataset_warnings": problems,
        "segmentation_warnings": seg_warnings,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }

    # ------------------------------------------------------------------ Part 1
    per_question = []
    for q in questions:
        doc, index = docs.get(q.contract), indexes.get(q.contract)
        if doc is None:
            continue
        gold_texts = [g.text for g in q.gold_evidence]
        row = {
            "qid": q.qid, "contract": q.contract, "type": q.type, "answerable": q.answerable,
            "question": q.question, "gold_roles": [g.role for g in q.gold_evidence], "retrieval": {},
        }

        gold_spans = [g.span for g in q.gold_evidence]
        row["gold_spans"] = gold_spans

        # Baseline context coverage (original full-document prompt). Only meaningful
        # when the data has real pages: the baseline cuts each page at 3,000 chars.
        if meta.get("paginated", True):
            context = _build_page_context(doc)
            nctx = ds.norm(context)
            row["baseline_context"] = {
                "chars": len(context),
                "est_tokens": round(len(context) / 4),  # rough chars/4 estimate, not a tokenizer count
                "gold_present": [ds.norm(t) in nctx for t in gold_texts],
                "gold_offsets": [nctx.find(ds.norm(t)) for t in gold_texts],
            }

        for v in variants:
            t0 = time.perf_counter()
            res = retrieve(index, q.question, top_k=max(ks), pool=max(max(ks), settings.EVIDENCE_CANDIDATE_POOL), **VARIANTS[v])
            elapsed = time.perf_counter() - t0
            hits = res["hits"]
            ranges = []
            for h in hits:
                c = index.clause(h.clause_id)
                ranges.append((c.char_start, c.char_end) if c.char_start is not None else None)
            rec = {
                "components": res["components"],
                "ranked": [h.clause_id for h in hits],
                "ranks": m.gold_ranks(gold_spans, ranges, args.span_threshold) if gold_spans else [],
                "top1": hits[0].to_dict() if hits else None,
                "seconds": round(elapsed, 4),
            }
            if gold_spans:
                for k in ks:
                    rec[f"char@{k}"] = {kk: round(vv, 4) for kk, vv in m.char_precision_recall(gold_spans, ranges, k).items()}
            if gold_spans and budgets:
                # Separate, wider retrieval so small clauses can fill a large budget
                wide = retrieve(index, q.question, top_k=args.budget_pool, pool=args.budget_pool, **VARIANTS[v])["hits"]
                wide_clauses = [index.clause(h.clause_id) for h in wide]
                for b in budgets:
                    chosen = m.fill_budget([len(c.text) for c in wide_clauses], b)
                    sel = [
                        (wide_clauses[i].char_start, min(wide_clauses[i].char_end, wide_clauses[i].char_start + taken))
                        for i, taken in chosen if wide_clauses[i].char_start is not None
                    ]
                    ranks = m.gold_ranks(gold_spans, sel, args.span_threshold)
                    pr = m.char_precision_recall(gold_spans, sel, len(sel))
                    rec[f"budget@{b}"] = {
                        "complete": float(all(r is not None for r in ranks)),
                        "recall": sum(r is not None for r in ranks) / len(ranks),
                        "char_recall": round(pr["char_recall"], 4),
                        "char_precision": round(pr["char_precision"], 4),
                        "clauses": len(sel),
                        "chars": sum(taken for _, taken in chosen),
                    }
            row["retrieval"][v] = rec
        per_question.append(row)

    summary = {"retrieval": {}, "baseline_context": {}}
    for v in variants:
        rows = [
            {**r, "ranks": r["retrieval"][v]["ranks"],
             **{key: val for key, val in r["retrieval"][v].items() if key.startswith("char@")}}
            for r in per_question
        ]
        s = m.summarize_retrieval(rows, ks)
        for b in budgets:
            vals = [r["retrieval"][v][f"budget@{b}"] for r in per_question
                    if r["answerable"] and f"budget@{b}" in r["retrieval"][v]]
            if vals:
                for key in ("complete", "char_recall", "char_precision", "clauses", "chars"):
                    s[f"budget{b}_{key}"] = round(mean(x[key] for x in vals), 4 if key not in ("clauses", "chars") else 1)
            by_type = s.get("by_type", {})
            for t in by_type:
                tv = [r["retrieval"][v][f"budget@{b}"]["complete"] for r in per_question
                      if r["answerable"] and r["type"] == t and f"budget@{b}" in r["retrieval"][v]]
                if tv:
                    by_type[t][f"budget{b}_complete"] = round(mean(tv), 4)
        comps = {k for r in per_question for k, on in r["retrieval"][v]["components"].items() if on}
        s["components_used"] = sorted(comps)
        if any(VARIANTS[v][f"use_{c}"] and c not in comps for c in ("dense", "rerank")):
            s["WARNING"] = "a requested component was unavailable; see model_load_errors in config.json"
        # Descriptive only: top-1 scores for answerable vs unanswerable questions
        for label, flag in (("answerable", True), ("unanswerable", False)):
            tops = [r["retrieval"][v]["top1"] for r in per_question if r["answerable"] == flag and r["retrieval"][v]["top1"]]
            key = "rerank_score" if VARIANTS[v]["use_rerank"] else ("dense_score" if not VARIANTS[v]["use_bm25"] else "bm25_score")
            vals = [t[key] for t in tops if t.get(key) is not None]
            if vals:
                s[f"mean_top1_{key}_{label}"] = round(mean(vals), 4)
        summary["retrieval"][v] = s

    answerable = [r for r in per_question if r["answerable"] and r["gold_roles"] and "baseline_context" in r]
    if not meta.get("paginated", True):
        summary["baseline_context"] = {"skipped": "dataset has no page layout; the baseline's per-page cut cannot be reproduced"}
    elif answerable:
        items = [p for r in answerable for p in r["baseline_context"]["gold_present"]]
        summary["baseline_context"] = {
            "gold_items_present": f"{sum(items)}/{len(items)}",
            "questions_with_all_gold_present": f"{sum(all(r['baseline_context']['gold_present']) for r in answerable)}/{len(answerable)}",
            "est_prompt_tokens_by_contract": {n: round(len(_build_page_context(d)) / 4) for n, d in docs.items()},
        }
        if args.assumed_num_ctx:
            # Gold text whose position in the prompt lies beyond the assumed window (rough, chars/4)
            beyond = [
                off >= 0 and off / 4 > args.assumed_num_ctx
                for r in answerable for off in r["baseline_context"]["gold_offsets"]
            ]
            summary["baseline_context"]["assumed_num_ctx"] = args.assumed_num_ctx
            summary["baseline_context"]["gold_items_beyond_assumed_window"] = f"{sum(beyond)}/{len(beyond)}"

    # ------------------------------------------------------------------ Part 2
    if args.with_llm:
        summary["llm"] = asyncio.run(_run_llm(args, questions, docs, indexes, per_question, settings, m, run_dir))

    # ------------------------------------------------------------------ Write
    with open(run_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)
    with open(run_dir / "per_question.jsonl", "w", encoding="utf-8") as f:
        for r in per_question:
            f.write(json.dumps(r, default=str) + "\n")
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    (run_dir / "summary.md").write_text(_summary_md(summary, config, ks), encoding="utf-8")

    print((run_dir / "summary.md").read_text(encoding="utf-8"))
    print(f"\nResults written to {run_dir}")


async def _run_llm(args, questions, docs, indexes, per_question, settings, m, run_dir):
    import httpx
    from app.services import chat_service
    from app.services.evidence import store as evidence_store

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            (await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")).raise_for_status()
    except Exception as e:
        print(f"Ollama not reachable at {settings.OLLAMA_BASE_URL} ({e}); skipping --with-llm part.")
        return {"skipped": f"Ollama not reachable: {e}"}

    # Reuse the indexes already built (same documents, same ids)
    for name, doc in docs.items():
        evidence_store._store[doc.id] = indexes[name]

    modes = [x.strip() for x in args.qa_modes.split(",") if x.strip()]
    by_qid = {r["qid"]: r for r in per_question}
    original_mode = settings.QA_MODE
    grading = []
    try:
        for mode in modes:
            settings.QA_MODE = mode
            for q in questions:
                doc = docs.get(q.contract)
                if doc is None:
                    continue
                t0 = time.perf_counter()
                try:
                    res = await chat_service.answer_document_question(doc, q.question)
                    err = None
                except Exception as e:
                    res, err = {"answer": "", "sources": []}, str(e)
                elapsed = time.perf_counter() - t0
                excerpts = [s.get("excerpt", "") for s in res.get("sources", [])]
                rec = {
                    "answer": res.get("answer", ""),
                    "sources": res.get("sources", []),
                    "error": err,
                    "seconds": round(elapsed, 2),
                    "abstained_heuristic": bool(m.ABSTAIN_RE.search(res.get("answer", ""))),
                    "citation_hits_gold": m.citation_hits_gold(excerpts, [g.text for g in q.gold_evidence]) if q.gold_evidence else None,
                    "any_verified_excerpt": any(s.get("excerpt_verified") for s in res.get("sources", [])),
                    "retrieval_clauses": [c["clause_id"] for c in res.get("retrieval", {}).get("clauses", [])],
                }
                by_qid[q.qid].setdefault("llm", {})[mode] = rec
                grading.append({
                    "qid": q.qid, "mode": mode, "type": q.type, "answerable": q.answerable,
                    "question": q.question, "gold_answer": q.gold_answer, "answer": rec["answer"],
                    "citations": " | ".join(f"p{s.get('page')}: {s.get('excerpt', '')}" for s in rec["sources"]),
                    "abstained_heuristic": rec["abstained_heuristic"],
                    "correct (y/n/partial)": "", "grounded (y/n)": "", "notes": "",
                })
                print(f"[{mode}] {q.qid} {elapsed:.1f}s abstain={rec['abstained_heuristic']}")
    finally:
        settings.QA_MODE = original_mode

    with open(run_dir / "grading.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(grading[0].keys()) if grading else ["qid"])
        writer.writeheader()
        writer.writerows(grading)

    out = {}
    for mode in modes:
        recs = [(r, r["llm"][mode]) for r in per_question if mode in r.get("llm", {})]
        ans = [x for r, x in recs if r["answerable"]]
        una = [x for r, x in recs if not r["answerable"]]
        out[mode] = {
            "n": len(recs),
            "errors": sum(1 for _, x in recs if x["error"]),
            "mean_seconds": round(mean(x["seconds"] for _, x in recs), 2) if recs else None,
            "answerable_abstained_heuristic": f"{sum(x['abstained_heuristic'] for x in ans)}/{len(ans)}",
            "unanswerable_abstained_heuristic": f"{sum(x['abstained_heuristic'] for x in una)}/{len(una)}",
            "answerable_citation_hits_gold": f"{sum(bool(x['citation_hits_gold']) for x in ans)}/{len(ans)}",
            "note": "Abstention and citation checks are heuristics; grade correctness in grading.csv.",
        }
    return out


def _summary_md(summary, config, ks):
    lines = [
        "# Evaluation run",
        "",
        f"- Started: {config['started']}",
        f"- Data: `{config['data']}` ({config['questions']} questions)",
        f"- Source: {config['dataset_meta'].get('source', 'local')}",
        f"- Setting: {config['setting']}",
        f"- A gold span counts as retrieved when the top-k clauses cover >= {config['span_threshold']:.0%} of it",
        f"- Dataset warnings: {len(config['dataset_warnings'])}; gold spans crossing clause boundaries: {len(config['segmentation_warnings'])}",
        f"- Model load errors: {config['model_load_errors'] or 'none'}",
        "",
        "## Retrieval (answerable questions)",
        "",
    ]
    all_cols = ["n", "mrr"] + [f"hit@{k}" for k in ks] + [f"complete@{k}" for k in ks] + \
        [f"char_recall@{k}" for k in ks] + [f"char_precision@{k}" for k in ks] + \
        [f"primary_recall@{k}" for k in ks] + [f"dependency_recall@{k}" for k in ks]
    # Drop columns no variant has (e.g. dependency recall on datasets without dependency roles)
    cols = [c for c in all_cols if any(c in s for s in summary["retrieval"].values())]
    lines.append("| variant | " + " | ".join(cols) + " |")
    lines.append("|---|" + "---|" * len(cols))
    for v, s in summary["retrieval"].items():
        lines.append(f"| {v} | " + " | ".join(str(s.get(c, "")) for c in cols) + " |")
    lines.append("")
    bkeys = sorted({k for s in summary["retrieval"].values() for k in s if k.startswith("budget")},
                   key=lambda k: (int(k[6:].split("_")[0]), k))
    if bkeys:
        lines += ["### Equal text budget (what fits in the prompt)", ""]
        lines.append("| variant | " + " | ".join(bkeys) + " |")
        lines.append("|---|" + "---|" * len(bkeys))
        for v, s in summary["retrieval"].items():
            lines.append(f"| {v} | " + " | ".join(str(s.get(k, "")) for k in bkeys) + " |")
        lines.append("")
    types = sorted({t for s in summary["retrieval"].values() for t in s.get("by_type", {})})
    if len(types) > 1:
        lines += ["### complete@k by question type", ""]
        tcols = [f"complete@{k}" for k in ks]
        lines.append("| variant | type | n | " + " | ".join(tcols) + " |")
        lines.append("|---|---|---|" + "---|" * len(tcols))
        for v, s in summary["retrieval"].items():
            for t in types:
                b = s.get("by_type", {}).get(t)
                if b:
                    lines.append(f"| {v} | {t} | {b['n']} | " + " | ".join(str(b.get(c, "")) for c in tcols) + " |")
        lines.append("")
    for v, s in summary["retrieval"].items():
        if s.get("WARNING"):
            lines.append(f"- **{v}**: {s['WARNING']}")
    lines += ["", "## Baseline (full-document prompt) coverage", ""]
    for k, val in summary.get("baseline_context", {}).items():
        lines.append(f"- {k}: {val}")
    if "llm" in summary:
        lines += ["", "## Chat pipeline (heuristic checks; grade grading.csv by hand)", ""]
        for mode, s in summary["llm"].items():
            lines.append(f"- **{mode}**: {s}")
    lines += ["", "_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
