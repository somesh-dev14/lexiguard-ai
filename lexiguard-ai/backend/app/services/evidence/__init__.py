"""
Evidence index for LexiGuard AI (experimental extension).

Builds a clause-level index of an uploaded document at upload time:
clause records with section numbers, defined terms, cross-references and
override markers, plus a BM25 index and (optionally) dense embeddings.

The plain retrieval baseline (B1) uses this index when settings.QA_MODE is
"retrieval". The default QA_MODE ("baseline") keeps the original
full-document chat behaviour.
"""
