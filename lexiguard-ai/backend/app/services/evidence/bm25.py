"""
Minimal BM25 (Okapi) over clause texts. Pure Python, no extra dependency.

Tokenization: lowercase alphanumeric tokens, a small English/legal stopword
list, and light plural stripping. Queries and documents use the same function.
"""

import math
import re
from collections import Counter
from typing import List

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "by", "with",
    "as", "at", "be", "is", "are", "was", "were", "it", "its", "this", "that",
    "these", "those", "from", "any", "all", "such", "which", "who", "what",
    "when", "where", "how", "does", "do", "can", "will", "would", "there",
    "has", "have", "had", "not", "but", "if", "than", "then", "into", "under",
    "about", "our", "we", "us", "you", "your", "i", "me", "my",
}


def tokenize(text: str) -> List[str]:
    tokens = []
    for tok in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if tok in _STOPWORDS:
            continue
        if len(tok) > 4 and tok.endswith("ies"):
            tok = tok[:-3] + "y"
        elif len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


class BM25:
    def __init__(self, docs: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(d) for d in docs]
        self.doc_freqs = [Counter(t) for t in self.doc_tokens]
        self.doc_lens = [len(t) for t in self.doc_tokens]
        self.n_docs = len(docs)
        self.avgdl = (sum(self.doc_lens) / self.n_docs) if self.n_docs else 0.0
        df: Counter = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        # BM25+ style non-negative idf
        self.idf = {
            term: math.log(1.0 + (self.n_docs - n + 0.5) / (n + 0.5)) for term, n in df.items()
        }

    def scores(self, query: str) -> List[float]:
        q_terms = tokenize(query)
        out = []
        for freqs, dl in zip(self.doc_freqs, self.doc_lens):
            s = 0.0
            for term in q_terms:
                f = freqs.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0))
                s += self.idf.get(term, 0.0) * (f * (self.k1 + 1)) / denom
            out.append(s)
        return out
