from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from security_agent.config import get_settings


TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_./:-]+")


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    path: Path
    content: str


@dataclass(frozen=True)
class KnowledgeHit:
    title: str
    source: str
    snippet: str
    score: float


def tokenize(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
    # Add single Chinese characters as a lightweight fallback for short queries.
    tokens.extend([char for char in text if "\u4e00" <= char <= "\u9fff"])
    return tokens


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or get_settings().knowledge_dir
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.documents = self._load_documents()
        self.document_tokens = [tokenize(doc.content + " " + doc.title) for doc in self.documents]
        self.document_frequency = self._build_document_frequency()

    def search(self, query: str, top_k: int | None = None) -> list[KnowledgeHit]:
        if not query.strip() or not self.documents:
            return []
        top_k = top_k or get_settings().top_k
        query_tokens = tokenize(query)
        scored: list[tuple[float, KnowledgeDocument]] = []
        for document, tokens in zip(self.documents, self.document_tokens):
            score = self._score(query_tokens, tokens)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            KnowledgeHit(
                title=document.title,
                source=str(document.path.relative_to(self.knowledge_dir.parent)),
                snippet=self._snippet(document.content, query_tokens),
                score=round(score, 4),
            )
            for score, document in scored[:top_k]
        ]

    def _load_documents(self) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []
        for path in sorted(self.knowledge_dir.rglob("*")):
            if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            title = self._extract_title(content) or path.stem
            documents.append(KnowledgeDocument(title=title, path=path, content=content))
        return documents

    def _build_document_frequency(self) -> dict[str, int]:
        frequency: dict[str, int] = {}
        for tokens in self.document_tokens:
            for token in set(tokens):
                frequency[token] = frequency.get(token, 0) + 1
        return frequency

    def _score(self, query_tokens: list[str], document_tokens: list[str]) -> float:
        if not query_tokens or not document_tokens:
            return 0.0
        token_counts: dict[str, int] = {}
        for token in document_tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        doc_count = max(len(self.documents), 1)
        score = 0.0
        for token in query_tokens:
            term_frequency = token_counts.get(token, 0)
            if term_frequency == 0:
                continue
            document_frequency = self.document_frequency.get(token, 1)
            inverse_document_frequency = math.log((doc_count + 1) / document_frequency)
            score += (1 + math.log(term_frequency)) * (1 + inverse_document_frequency)
        return score

    @staticmethod
    def _extract_title(content: str) -> str | None:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return None

    @staticmethod
    def _snippet(content: str, query_tokens: list[str], window: int = 120) -> str:
        normalized = content.replace("\n", " ")
        lower = normalized.lower()
        positions = [lower.find(token.lower()) for token in query_tokens if token and lower.find(token.lower()) >= 0]
        start = min(positions) if positions else 0
        start = max(start - 30, 0)
        snippet = normalized[start : start + window].strip()
        if start > 0:
            snippet = "..." + snippet
        if start + window < len(normalized):
            snippet += "..."
        return snippet

