"""Поиск похожих обращений.

# TODO: Replace with fine-tuned embedding model
# Current: category matching + keyword overlap
# Production: pgvector cosine similarity on fine-tuned embeddings

Placeholder: считает "похожесть" как комбинацию совпадения категории и доли
общих значимых слов (Jaccard по токенам). В проде — косинусная близость на
дообученных эмбеддингах через pgvector.
"""
import re

from models import SimilarTicket

_TOKEN_RE = re.compile(r"[а-яёқғүұһәіөңa-z]+", re.IGNORECASE)
_STOP = {
    "и", "в", "на", "с", "по", "не", "уже", "что", "как", "для", "это", "все",
    "нет", "да", "у", "к", "от", "за", "же", "бы", "то", "из", "но", "а", "о",
    "во", "до", "мен", "бен", "деп", "жоқ", "бар",
}


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 3 and t.lower() not in _STOP}


def find_similar(target: dict, pool: list[dict], top_k: int = 3) -> list[SimilarTicket]:
    """Найти top_k похожих обращений из pool (список dict-тикетов)."""
    target_tokens = _tokens(target["text"])
    target_category = target.get("category") or (target.get("_gold") or {}).get("category")

    scored: list[tuple[int, dict]] = []
    for cand in pool:
        if cand["id"] == target["id"]:
            continue
        cand_category = cand.get("category") or (cand.get("_gold") or {}).get("category")
        cand_tokens = _tokens(cand["text"])

        union = target_tokens | cand_tokens
        overlap = len(target_tokens & cand_tokens) / len(union) if union else 0.0

        # категория даёт основную массу похожести, пересечение слов — добавку
        category_bonus = 0.6 if cand_category and cand_category == target_category else 0.0
        score = category_bonus + overlap * 0.4
        similarity = round(min(0.99, max(0.05, score)) * 100)

        scored.append((similarity, cand))

    scored.sort(key=lambda x: x[0], reverse=True)
    result: list[SimilarTicket] = []
    for similarity, cand in scored[:top_k]:
        cand_category = cand.get("category") or (cand.get("_gold") or {}).get("category") or "—"
        result.append(
            SimilarTicket(
                id=cand["id"],
                text=cand["text"],
                category=cand_category,
                similarity_score=similarity,
            )
        )
    return result
