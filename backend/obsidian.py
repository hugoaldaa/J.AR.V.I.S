from pathlib import Path
import re
import json

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_PATH = BASE_DIR / "Obsidian"

MEMORY_DIR = VAULT_PATH / "01 - Memoria"
CONFIG_PATH = Path(__file__).resolve().parent / "memory_config.json"

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


# ============================================================
# CONFIGURACIÓN DE MEMORIA
# ============================================================

def load_memory_config():
    """
    Carga memory_config.json. Si falta o está corrupto,
    devuelve un config por defecto.
    """

    default = {
        "categorias": {
            "Datos Personales": {
                "archivo": "01 - Memoria/Datos Personales.md",
                "sensibilidad": "media",
                "reglas": [],
            },
            "Preferencias": {
                "archivo": "01 - Memoria/Preferencias.md",
                "sensibilidad": "baja",
                "reglas": [],
            },
        },
        "reglas_explicitas": {},
        "datos_sensibles": [],
        "clave_secrets": ".jarvis_memoria.key",
    }

    try:

        with open(
            CONFIG_PATH,
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data

    except Exception:

        return default


def get_category_config():
    """
    Devuelve la config de categorías como un dict.
    """

    config = load_memory_config()

    return config.get("categorias", {})


def infer_category(text: str) -> str:
    """
    Intenta adivinar la categoría a partir de las reglas
    del config. Devuelve None si no la encuentra.
    """

    text_lower = text.lower()

    categories = get_category_config()

    for name, settings in categories.items():

        for regla in settings.get("reglas", []):

            if regla in text_lower:
                return name

    return None


# ============================================================
# ESCRITURA DE MEMORIA
# ============================================================

def _get_or_create_note(category: str) -> Path:
    """
    Devuelve la ruta del archivo para una categoría,
    creándolo si no existe.
    """

    config = load_memory_config()

    categories = config.get("categorias", {})

    settings = categories.get(category, {})

    archivo = settings.get("archivo")

    if not archivo:

        # Categoría desconocida: crear un archivo propio
        archivo = f"01 - Memoria/{category}.md"

    note_path = VAULT_PATH / archivo

    note_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not note_path.exists():

        note_path.write_text(
            f"# {category}\n\n",
            encoding="utf-8"
        )

    return note_path


def save_memory_entry(category: str, content: str) -> str:
    """
    Guarda o actualiza un dato en la memoria de Obsidian.

    Si content ya existe (igual o por substring), no duplica.
    Devuelve:
        "saved"    -> se creó un dato nuevo
        "updated"  -> se actualizó uno existente
    """

    content = content.strip()

    if not content:
        return "saved"

    note_path = _get_or_create_note(category)

    # Leer el contenido actual
    existing = note_path.read_text(
        encoding="utf-8"
    )

    # Comprobar si ya existe (por substring en una línea)
    lines = existing.splitlines()

    found_index = None

    for i, line in enumerate(lines):

        if content.lower() in line.lower():
            found_index = i
            break

    if found_index is not None:

        lines[found_index] = f"- {content}"

        note_path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8"
        )

        return "updated"

    # Añadir una línea nueva al final del archivo
    if existing and not existing.endswith(("\n", " ")):
        existing += "\n"

    if existing and not existing.endswith("\n\n"):
        existing += "\n"

    note_path.write_text(
        existing + f"- {content}\n",
        encoding="utf-8"
    )

    return "saved"


def upsert_memory_entry(
    category: str,
    label: str,
    content: str
) -> str:
    """
    Si ya existe una línea que empieza por 'label:',
    la sustituye por la nueva (actualización).
    Si no existe, la añade al final.

    label sería p.ej. "Nombre", "Edad", "Cumpleaños".

    Devuelve "saved" o "updated".
    """

    note_path = _get_or_create_note(category)

    existing = note_path.read_text(
        encoding="utf-8"
    )

    lines = existing.splitlines()

    prefix = label.lower() + ":"

    replaced = False
    new_lines = []

    for line in lines:

        line_lower = line.lower().lstrip("- ")

        if line_lower.startswith(prefix):

            new_lines.append(f"- {content}")
            replaced = True

        else:

            new_lines.append(line)

    if not replaced:

        text = "\n".join(new_lines)

        if text and not text.endswith("\n"):

            text += "\n"

        if text and not text.endswith("\n"):

            text += "\n"

        note_path.write_text(
            text + f"- {content}\n",
            encoding="utf-8"
        )

        return "saved"

    note_path.write_text(
        "\n".join(new_lines) + "\n",
        encoding="utf-8"
    )

    return "updated"


def update_memory_entry(
    category: str,
    old_content: str,
    new_content: str
) -> str:
    """
    Sustituye un dato existente por otro nuevo.
    Devuelve "updated" o "not_found".
    """

    note_path = _get_or_create_note(category)

    existing = note_path.read_text(
        encoding="utf-8"
    )

    if old_content.lower() not in existing.lower():

        return "not_found"

    updated = re.sub(
        re.escape(old_content),
        new_content,
        existing,
        flags=re.IGNORECASE
    )

    note_path.write_text(
        updated,
        encoding="utf-8"
    )

    return "updated"


def delete_memory_entry(
    category: str,
    content_contains: str
) -> str:
    """
    Borra de la memoria las líneas que contengan
    content_contains.
    Devuelve "deleted" o "not_found".
    """

    note_path = _get_or_create_note(category)

    existing = note_path.read_text(
        encoding="utf-8"
    )

    lines = existing.splitlines()

    remaining = [
        line
        for line in lines
        if content_contains.lower() not in line.lower()
    ]

    if len(remaining) == len(lines):

        return "not_found"

    # Solo reescribe si hubo cambios
    if remaining:

        note_path.write_text(
            "\n".join(remaining).rstrip() + "\n",
            encoding="utf-8"
        )

    else:

        note_path.write_text(
            f"# {category}\n\n",
            encoding="utf-8"
        )

    return "deleted"