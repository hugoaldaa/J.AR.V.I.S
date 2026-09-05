from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_PATH = BASE_DIR / "Obsidian"

# Palabras que normalmente no aportan información a la búsqueda
STOPWORDS = {
    "que", "qué", "como", "cómo", "cual", "cuál",
    "quien", "quién", "donde", "dónde",
    "para", "por", "con", "una", "uno",
    "las", "los", "del", "el", "la",
    "de", "en", "y", "o", "es",
    "estamos", "está", "están",
    "usando", "usar", "utilizamos",
    "tenemos", "crear", "creando",
}


def get_keywords(query: str):
    """
    Extrae las palabras importantes de una pregunta.
    """

    words = re.findall(r"[a-záéíóúüñ]+", query.lower())

    keywords = [
        word
        for word in words
        if word not in STOPWORDS and len(word) >= 3
    ]

    return keywords


def search_vault(query: str, max_results: int = 5):
    """
    Busca notas de Obsidian relacionadas con la pregunta.
    """

    if not VAULT_PATH.exists():
        return []

    keywords = get_keywords(query)

    if not keywords:
        return []

    results = []

    for file in VAULT_PATH.rglob("*.md"):

        try:
            content = file.read_text(encoding="utf-8")
        except Exception:
            continue

        content_lower = content.lower()

        # Contamos cuántas palabras importantes aparecen
        score = 0

        for keyword in keywords:
            if keyword in content_lower:
                score += 1

        if score > 0:
            results.append({
                "file": str(file),
                "content": content,
                "score": score
            })

    # Primero las notas con más coincidencias
    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return results[:max_results]