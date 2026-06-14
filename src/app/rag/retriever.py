import unicodedata

from app.rag.corpus import CORPUS


def _normalize(text: str) -> str:
    """Lowercase y elimina tildes para matching robusto entre variantes ortográficas."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()


def retrieve(
    message: str,
    url_reasons: list[str] | None = None,
    text_patterns: list[str] | None = None,
    extra_context: str = "",
    top_k: int = 2,
) -> str:
    """
    Dado el mensaje actual y los indicadores del análisis heurístico,
    devuelve un bloque de texto con las fichas de conocimiento más relevantes
    para inyectar como contexto en el prompt de la IA.

    Retorna string vacío si no hay matches con score > 0.
    """
    url_reasons = url_reasons or []
    text_patterns = text_patterns or []

    search_parts = [message] + url_reasons + text_patterns
    if extra_context:
        search_parts.append(extra_context)
    search_text = _normalize(" ".join(search_parts))

    if not search_text.strip():
        return ""

    scored: list[tuple[int, dict]] = []
    for entry in CORPUS:
        score = sum(1 for kw in entry["keywords"] if _normalize(kw) in search_text)
        if score > 0:
            scored.append((score, entry))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [entry for _, entry in scored[:top_k]]

    sections = [f"### {e['title']}\n{e['content']}" for e in top]
    return "\n\n".join(sections)
