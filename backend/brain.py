import re
import json
import requests

from obsidian import (
    search_vault,
    infer_category,
    load_memory_config,
    upsert_memory_entry,
    save_memory_entry,
)
from database import (
    save_message,
    get_conversation,
)

from system_tools import (
    AVAILABLE_FUNCTIONS,
    open_program,
    save_memory,
    update_memory,
    delete_memory,
)


# ============================================================
# ELIMINAR EMOJIS
# ============================================================

def remove_emojis(text: str) -> str:

    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "\U00002600-\U000026FF"
        "\U00002300-\U000023FF"
        "]+",
        flags=re.UNICODE
    )

    return emoji_pattern.sub("", text).strip()


# ============================================================
# CONFIGURACIÓN
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"

MODEL = "qwen3:8b"

SESSION_ID = "default"

# Mantener el modelo cargado en memoria 12 horas para
# evitar recargas de ~25s entre mensajes.
KEEP_ALIVE = "12h"


# ============================================================
# PERSONALIDAD
# ============================================================

SYSTEM_PROMPT = """
Te llamas J.A.R.V.I.S.

Eres el asistente personal local del usuario.

PERSONALIDAD:
- Eres inteligente, educado y profesional.
- Eres tranquilo y seguro de ti mismo.
- Tienes un humor sutil e ingenioso cuando encaja.
- Eres directo.
- No das explicaciones innecesariamente largas.
- Si el usuario necesita una explicación detallada,
  puedes extenderte.
- Hablas de forma natural.
- No eres excesivamente formal ni robótico.
- No repitas constantemente el nombre del usuario.
- Nunca inventes información.

IDENTIDAD:
- Tu nombre es J.A.R.V.I.S.
- Eres el asistente personal del usuario.
- Funcionas localmente en su ordenador.
- Puedes utilizar herramientas del sistema cuando sea necesario.

MEMORIA:
Puedes utilizar:
1. El historial de conversaciones almacenado en SQLite.
2. La memoria permanente almacenada en Obsidian.

Utiliza estos datos cuando sean relevantes.

REGLAS:
- No inventes datos personales.
- SI NUNCA te han dicho el nombre del usuario, NUNCA lo inventes.
- Si el usuario pregunta por su nombre y no lo tienes guardado, di que no lo sabes.
- Si no recuerdas algo, dilo claramente.
- Si un dato aparece en el historial, puedes utilizarlo.
- Si un dato aparece en Obsidian, puedes utilizarlo.
- No afirmes recordar algo que no aparece en tu contexto.

HERRAMIENTAS:
Tienes herramientas para consultar información del ordenador
y realizar determinadas acciones.

IMPORTANTE:
- Cuando necesites información real del ordenador,
  utiliza la herramienta correspondiente.
- No inventes información del sistema.
- Cuando el usuario pida la hora, utiliza get_time.
- Cuando el usuario pregunte la fecha, utiliza get_date.
- Cuando pregunte por el ordenador, utiliza get_system_info.
- Cuando quiera abrir un programa, utiliza open_program.
- Cuando quiera abrir una carpeta, utiliza open_folder.
- Cuando quiera abrir una página web, utiliza open_website.
- Cuando pregunte por el tiempo meteorológico,
  utiliza get_weather.

COMUNICACIÓN:
- Responde siempre en español salvo que el usuario solicite
  otro idioma.
- Sé conciso cuando la pregunta sea sencilla.
- No utilices emojis ni emoticonos.
- Utiliza únicamente texto normal.
- No describas tu razonamiento interno.
- No digas que eres una IA salvo que el usuario pregunte.

ACCIONES:
- Cuando el usuario ordene abrir un programa, carpeta o página web,
  debe ejecutarse la acción.
- No preguntes nada antes de ejecutar una orden clara.
- No digas "Hecho".
- No digas "Listo".
- No digas "Ya está".
- No preguntes si el usuario necesita algo más.
- Las órdenes de apertura deben ejecutarse de forma silenciosa.

MEMORIA PERMANENTE:
Tienes herramientas para GUARDAR, ACTUALIZAR y BORRAR memoria.
Úsalas para recordar datos importantes del usuario a largo plazo.

CUÁNDO GUARDAR (sin preguntar):
- Cuando el usuario te dice un dato personal nuevo
  (su nombre, dónde vive, su profesión, su email...).
  - Usa save_memory con category "Datos Personales".
- Cuando te cuenta una preferencia ("me gusta X",
  "prefiero X", "mi favorito es X").
  - Usa save_memory con category "Preferencias".
- Cuando te cuenta un plan o tarea futura.
  - Usa save_memory con category "Planes y Tareas".
- Cuando te cuente una iniciativa o proyecto propio.
  - Usa save_memory con category "Proyectos".

CÓMO GUARDAR:
- Llama save_memory(category, content, confirm=False)
  para datos normales.
- Guarda una frase concreta y útil. No dupliques datos
  que ya estén en la memoria.

CUÁNDO PEDIR CONFIRMACIÓN (dato sensible):
- Si el dato parece sensible (contraseñas, PIN, DNI,
  tarjetas, IBAN, seguridad social), NO lo guardes
  directamente.
- Responde pidiendo confirmación al usuario,
  por ejemplo: "¿Quieres que lo guarde cifrado?"
- No inventes ni muestres el dato de nuevo.

CUÁNDO ACTUALIZAR:
- Si el usuario corrige un dato que guardabas antes
  ("no vivo en Madrid, vivo en Barcelona"),
  usa update_memory con la categoría correspondiente.

CUÁNDO BORRAR:
- Si el usuario pide olvidar o borrar algo de tu memoria,
  usa delete_memory con la categoría y parte del contenido.

RECUPERAR DATOS:
- Los datos guardados en Obsidian aparecen en tu contexto
  como memoria permanente.
- Se guardan automáticamente en tu contexto al preguntar.
- NUNCA inventes datos personales. Si no están en tu
  contexto, dilo: "No tengo ese dato guardado".
"""


# ============================================================
# TOOLS PARA OLLAMA
# ============================================================

TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Obtiene la hora actual del ordenador.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Obtiene la fecha actual del ordenador.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": (
                "Obtiene información real del ordenador, "
                "como CPU, RAM y discos."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "open_program",
            "description": (
                "Abre un programa instalado en el ordenador."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program": {
                        "type": "string",
                        "description": (
                            "Nombre del programa que se quiere abrir."
                        ),
                    }
                },
                "required": ["program"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Abre una carpeta existente de Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta de la carpeta.",
                    }
                },
                "required": ["path"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": (
                "Abre una página web en el navegador predeterminado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Dirección de la página web.",
                    }
                },
                "required": ["url"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Obtiene el tiempo meteorológico actual de una ciudad."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nombre de la ciudad.",
                    }
                },
                "required": ["city"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Guarda un dato permanente del usuario en la memoria. "
                "Categorías: 'Datos Personales', 'Preferencias', "
                "'Planes y Tareas', 'Proyectos'. Para datos sensibles "
                "usa confirm=True para pedir confirmación antes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Categoría de la memoria: 'Datos Personales', "
                            "'Preferencias', 'Planes y Tareas' o 'Proyectos'."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "Dato que se quiere recordar.",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": (
                            "Ponlo a true si es un dato sensible y hace "
                            "falta confirmación del usuario. Default false."
                        ),
                    },
                },
                "required": ["category", "content"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": (
                "Actualiza un dato ya guardado en la memoria cuando el "
                "usuario corrige o cambia información previa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría de la memoria.",
                    },
                    "old_content": {
                        "type": "string",
                        "description": "El dato antiguo a sustituir.",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "El dato nuevo que lo reemplaza.",
                    },
                },
                "required": ["category", "old_content", "new_content"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": (
                "Borra de la memoria los datos que coincidan con "
                "content_contains. Se usa cuando el usuario pide "
                "olvidar o borrar algo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría de la memoria.",
                    },
                    "content_contains": {
                        "type": "string",
                        "description": (
                            "Parte del contenido a eliminar (coincidencia "
                            "parcial, sin distinguir mayúsculas)."
                        ),
                    },
                },
                "required": ["category", "content_contains"],
            },
        },
    },
]


# ============================================================
# MEMORIA EN SESIÓN (datos sensibles pendientes de confirmar)
# ============================================================

_pending_confirm = None


def _reset_pending_confirm():
    global _pending_confirm
    _pending_confirm = None


def _set_pending_confirm(category: str, content: str):
    global _pending_confirm
    _pending_confirm = {
        "category": category,
        "content": content,
    }


# ============================================================
# MEMORIA OBSIDIAN
# ============================================================

def get_memory(query: str) -> str:

    results = search_vault(query)

    if not results:
        return ""

    memory = []

    for result in results:

        memory.append(
            f"Archivo: {result['file']}\n"
            f"{result['content']}"
        )

    return "\n\n---\n\n".join(memory)


# ============================================================
# HISTORIAL
# ============================================================

def get_chat_history(
    session_id: str = SESSION_ID,
    limit: int = 20
):

    return get_conversation(
        session_id,
        limit
    )


# ============================================================
# EJECUTAR TOOL
# ============================================================

def execute_tool(tool_name, arguments):

    function = AVAILABLE_FUNCTIONS.get(tool_name)

    if function is None:

        return (
            f"Error: herramienta desconocida "
            f"'{tool_name}'."
        )

    try:

        result = function(
            **arguments
        )

        return str(result)

    except Exception as e:

        return (
            f"Error ejecutando "
            f"{tool_name}: {e}"
        )


# ============================================================
# COMANDOS DIRECTOS
# ============================================================

def handle_direct_command(message: str):

    text = message.lower().strip()

    # --------------------------------------------------------
    # PALABRAS QUE INDICAN QUE QUIERE ABRIR ALGO
    # --------------------------------------------------------

    open_words = [
        "abre ",
        "abrir ",
        "inicia ",
        "iniciar ",
        "lanza ",
        "lanzar ",
        "ejecuta ",
        "ejecutar ",
    ]

    if not any(
        text.startswith(word)
        for word in open_words
    ):
        return None

    # --------------------------------------------------------
    # PROGRAMAS PERMITIDOS
    # --------------------------------------------------------

    programs = {
        "calculadora": "calculadora",
        "calculator": "calculator",

        "google chrome": "google chrome",
        "chrome": "chrome",

        "microsoft edge": "microsoft edge",
        "edge": "edge",

        "firefox": "firefox",

        "visual studio code": "visual studio code",
        "vs code": "vs code",
        "vscode": "vscode",

        "obsidian": "obsidian",
        "discord": "discord",
        "spotify": "spotify",
        "steam": "steam",

        "bloc de notas": "bloc de notas",
        "notepad": "notepad",

        "explorador de archivos": "explorador de archivos",
        "explorador": "explorador",

        "terminal": "terminal",
    }

    # Ordenamos de mayor a menor longitud para que
    # "google chrome" se detecte antes que "chrome".
    program_names = sorted(
        programs.keys(),
        key=len,
        reverse=True
    )

    for name in program_names:

        if name in text:

            program = programs[name]

            result = open_program(program)

            # ÉXITO
            if result == "OK":
                return ""

            # ERROR
            return result

    # No era un programa conocido
    return None


# ============================================================
# JARVIS
# ============================================================

def write_messages(message: str) -> list:
    """
    Construye el contexto completo: personalidad + memoria
    de Obsidian + historial + mensaje nuevo.
    """

    memory = get_memory(message)
    history = get_chat_history()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if memory:

        messages.append(
            {
                "role": "system",
                "content": (
                    "MEMORIA PERMANENTE DE OBSIDIAN\n\n"
                    + memory
                )
            }
        )

    for role, content, created_at in history:

        if role in ["user", "assistant"]:

            # No añadimos respuestas vacías
            if content.strip():

                messages.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

    messages.append(
        {
            "role": "user",
            "content": message
        }
    )

    return messages


# ============================================================
# FASE 1 DE MEMORIA (reglas explícitas)
# ============================================================

_AFFIRMATIVE = [
    "sí",
    "si",
    "vale",
    "ok",
    "okey",
    "ok vale",
    "adelante",
    "claro",
    "por supuesto",
    "guárdalo",
    "guardalo",
    "dalo por hecho",
]

_NEGATIVE = [
    "no",
    "no quiero",
    "no guardes",
    "mejor no",
    "déjalo",
    "dejalo",
    "olvídalo",
    "olvida lo",
    "ignóralo",
]


def _is_affirmative(message: str) -> bool:
    text = message.lower().strip()

    # Puede ser una frase que empieza por "sí," etc.
    for word in _AFFIRMATIVE:

        if text == word:
            return True

        if text.startswith(word + " ") or text.startswith(word + ","):
            return True

    return False


def _is_negative(message: str) -> bool:
    text = message.lower().strip()

    for phrase in _NEGATIVE:

        if text == phrase:
            return True

        if text.startswith(phrase + " ") or text.startswith(phrase + ","):
            return True

    return False


def handle_memory_commands(message: str):
    """
    Procesa comandos explícitos de memoria en la Fase 1.

    Devuelve una tupla:
        (resultado_o_None, notice)
    donde resultado es una respuesta de texto (si se
    resolvió sin pasar al LLM), o None si debe continuar
    con el proceso normal.
    notice es un string para el feedback en la GUI, o "".
    """

    global _pending_confirm

    text = message.lower().strip()

    # ========================================================
    # 1) Confirmación pendiente de un dato sensible
    # ========================================================

    if _pending_confirm is not None:

        if _is_affirmative(message):

            category = _pending_confirm["category"]
            content = _pending_confirm["content"]

            _pending_confirm = None

            # Guardar cifrado (confirm=True forzará guardado)
            result = save_memory(
                category,
                content,
                confirm=False
            )

            notice = (
                "Dato sensible cifrado guardado "
                f"({category})."
            )

            save_message(
                SESSION_ID,
                "user",
                message
            )

            return (
                "He guardado ese dato de forma segura.",
                notice,
            )

        # Respuesta no afirmativa -> no guardar
        _pending_confirm = None

        save_message(
            SESSION_ID,
            "user",
            message
        )

        return (
            "De acuerdo, no lo guardo.",
            "",
        )

    # ========================================================
    # 2) Reglas explícitas del config
    # ========================================================

    config = load_memory_config()

    reglas_explicitas = config.get(
        "reglas_explicitas",
        {}
    )

    # Ordenar por longitud para que "borra de tu memoria"
    # se detecte antes que "borra"
    reglas_sorted = sorted(
        reglas_explicitas.keys(),
        key=len,
        reverse=True
    )

    for regla in reglas_sorted:

        if text.startswith(regla):

            accion = reglas_explicitas[regla].get("accion")

            rest = message[len(regla):].strip()

            if not rest:
                continue

            # Inferir categoría
            category = infer_category(rest)

            if category is None:
                category = infer_category(message)

            if category is None:
                category = "Datos Personales"

            # ---------- GUARDAR ----------
            if accion == "save":

                # Detectar sensibilidad
                if _is_sensitive_direct(category, rest):

                    # Guardar pendiente para confirmación
                    _pending_confirm = {
                        "category": category,
                        "content": rest,
                    }

                    save_message(
                        SESSION_ID,
                        "user",
                        message
                    )

                    return (
                        "Ese dato parece sensible. "
                        "¿Quieres que lo guarde cifrado?",
                        "",
                    )

                result = save_memory(category, rest)

                notice = f"Memoria guardada: {category}."

                save_message(
                    SESSION_ID,
                    "user",
                    message
                )

                return ("", notice)

            # ---------- BORRAR ----------
            if accion == "delete":

                result = delete_memory(category, rest)

                if result.startswith("OK"):

                    notice = (
                        f"Memoria borrada de {category}."
                    )

                    save_message(
                        SESSION_ID,
                        "user",
                        message
                    )

                    return ("", notice)

                notice = (
                    f"No encontré eso guardado en {category}."
                )

                save_message(
                    SESSION_ID,
                    "user",
                    message
                )

                return ("", notice)

    # ========================================================
    # 3) AUTO-SAVE (frases naturales: nombre, edad, gustos...)
    # ========================================================

    auto_notices = detect_auto_memory(message)

    if auto_notices:

        save_message(
            SESSION_ID,
            "user",
            message
        )

        # Devolvemos resultado None para que el LLM también
        # responda de forma conversacional al usuario.
        return (None, " ".join(auto_notices))

    # No se manejó con reglas
    return (None, "")


# ============================================================
# AUTO-SAVE (detección por regex de frases naturales)
# ============================================================

_AUTO_PATTERNS = [
    {
        "regex": r"\bme llamo\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Nombre",
    },
    {
        "regex": r"\bmi nombre es\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Nombre",
    },
    {
        "regex": r"\btengo\s+(\d+)\s+años",
        "category": "Datos Personales",
        "label": "Edad",
    },
    {
        "regex": r"\b(?:mi cumpleaños es|cumplo años el|nací el)\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Cumpleaños",
    },
    {
        "regex": r"\bvivo en\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Ciudad",
    },
    {
        "regex": r"\b(?:mi email es|mi correo es)\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Email",
    },
    {
        "regex": r"\b(?:trabajo de|soy)\s+(.+?)[?.!]*$",
        "category": "Datos Personales",
        "label": "Profesión",
    },
    {
        "regex": r"\bme gusta[n]?\s+(.+?)[?.!]*$",
        "category": "Preferencias",
        "label": "Gustos",
    },
    {
        "regex": r"\bmi favorito[a]? es\s+(.+?)[?.!]*$",
        "category": "Preferencias",
        "label": "Favorito",
    },
    {
        "regex": r"\bprefiero\s+(.+?)[?.!]*$",
        "category": "Preferencias",
        "label": "Prefiere",
    },
]


def detect_auto_memory(message: str):
    """
    Detecta frases naturales que revelan datos del usuario
    (nombre, edad, cumpleaños, ciudad, gustos...) y los guarda
    automáticamente en la categoría correspondiente.

    Devuelve un listado de noticias ["Memoria guardada: X", ...]
    o None si no detectó nada relevante.
    """

    text = message.strip()

    # No auto-guardar preguntas
    if text.lower().startswith((
        "qué", "que", "cuál", "cual", "dónde", "donde",
        "cómo", "como", "cuándo", "cuando", "quién",
        "quien", "por qué", "por que", "puedes", "ayúdame",
    )):
        return None

    notices = []

    for pattern in _AUTO_PATTERNS:

        match = re.search(
            pattern["regex"],
            message,
            re.IGNORECASE
        )

        if match is None:
            continue

        category = pattern["category"]
        label = pattern.get("label", "")

        # Construir contenido: "12/12/2004" -> "Cumpleaños: ..."
        value = match.group(1).strip()

        if label == "Cumpleaños":

            value = value.lstrip("el ").strip()
            content = f"Cumpleaños: {value}"

        elif label == "Edad":

            content = f"Edad: {value} años"

        else:

            content = f"{label}: {value}" if label else value

        # No guardar si el contenido parece sensible
        if _is_sensitive_direct(category, content):
            continue

        # Upsert por etiqueta: si ya existe, se actualiza
        if label:

            result = upsert_memory_entry(
                category,
                label,
                content
            )

        else:

            result = save_memory_entry(category, content)

        if result.startswith(("saved", "updated")):

            notices.append(
                f"Memoria guardada: {category}."
            )

    # Evitar duplicar la misma noticia (varios patrones
    # pueden coincidir en "mi nombre es X y vivo en Y")
    seen = set()
    unique = []

    for n in notices:

        if n not in seen:

            seen.add(n)
            unique.append(n)

    if not unique:
        return None

    return unique


def _is_sensitive_direct(category: str, content: str) -> bool:
    """
    Comprueba si un contenido parece sensible a partir
    del config (datos_sensibles).
    """

    config = load_memory_config()

    categories = config.get("categorias", {})

    settings = categories.get(category, {})

    if settings.get("sensibilidad") == "alta":
        return True

    sensitive_words = config.get("datos_sensibles", [])

    content_lower = content.lower()

    for word in sensitive_words:

        if word in content_lower:

            return True

    return False


def send_payload(messages: list, stream: bool = False):
    """
    Envia la petición a Ollama.

    Devuelve la respuesta completa parseada (stream=False)
    o un generador de líneas JSON (stream=True).

    Ante un error de conexión entrega el mensaje de error
    como un string.
    """

    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": stream,
        "think": False,
        "keep_alive": KEEP_ALIVE,
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=stream,
            timeout=120
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError:

        yield (
            "No puedo conectarme con Ollama. "
            "Comprueba que Ollama está iniciado."
        )

        return

    except requests.exceptions.Timeout:

        yield (
            "Ollama está tardando demasiado en responder."
        )

        return

    except Exception as e:

        yield f"Ha ocurrido un error: {e}"

        return

    if stream:

        for line in response.iter_lines():

            if not line:
                continue

            try:

                yield json.loads(
                    line.decode("utf-8")
                )

            except Exception:

                continue

        response.close()

    else:

        yield response.json()


# ============================================================
# CALENTAR MODELO (arranque)
# ============================================================

def warmup():
    """
    Petición mínima en segundo plano para que Ollama cargue
    el modelo en memoria. Evita los ~25s de arranque en frío
    en el primer mensaje.
    """

    try:

        list(
            send_payload(
                [
                    {
                        "role": "user",
                        "content": "ok"
                    }
                ],
                stream=False
            )
        )

    except Exception:

        pass


# ============================================================
# JARVIS (respuesta completa)
# ============================================================

def ask_jarvis(message: str) -> str:

    # ========================================================
    # COMANDOS DIRECTOS
    # ========================================================

    direct_result = handle_direct_command(message)

    if direct_result is not None:

        save_message(
            SESSION_ID,
            "user",
            message
        )

        # No guardamos una respuesta artificial.
        return direct_result

    # ========================================================
    # FASE 1 DE MEMORIA (reglas explícitas)
    # ========================================================

    memory_result, notice = handle_memory_commands(message)

    if notice:

        print(notice)

    if memory_result is not None:

        return memory_result

    # ========================================================
    # MENSAJES
    # ========================================================

    messages = write_messages(message)

    # ========================================================
    # AGENT LOOP
    # ========================================================

    while True:

        data = None

        for item in send_payload(messages, stream=False):

            # send_payload puede devolver un string de error
            if isinstance(item, str):
                return item

            data = item
            break

        if data is None:
            return (
                "No he recibido respuesta de Ollama."
            )

        # ====================================================
        # RESPUESTA DEL ASISTENTE
        # ====================================================

        assistant_message = data.get(
            "message",
            {}
        )

        messages.append(
            assistant_message
        )

        # ====================================================
        # TOOLS
        # ====================================================

        tool_calls = assistant_message.get(
            "tool_calls",
            []
        )

        # ====================================================
        # RESPUESTA NORMAL
        # ====================================================

        if not tool_calls:

            answer = (
                assistant_message
                .get("content", "")
                .strip()
            )

            # Eliminar emojis aunque Qwen los genere
            answer = remove_emojis(answer)

            save_message(
                SESSION_ID,
                "user",
                message
            )

            save_message(
                SESSION_ID,
                "assistant",
                answer
            )

            return answer

        # ====================================================
        # EJECUTAR TOOLS
        # ====================================================

        for tool_call in tool_calls:

            function_data = (
                tool_call
                .get("function", {})
            )

            tool_name = function_data.get(
                "name"
            )

            arguments = function_data.get(
                "arguments",
                {}
            )

            print(
                f"Herramienta: {tool_name}"
            )

            print(
                f"Argumentos: {arguments}"
            )

            result = execute_tool(
                tool_name,
                arguments
            )

            print(
                f"Resultado: {result}"
            )

            # ------------------------------------------------
            # ACCIONES DE APERTURA
            # ------------------------------------------------

            if tool_name in [
                "open_program",
                "open_folder",
                "open_website"
            ]:

                if result == "OK":

                    save_message(
                        SESSION_ID,
                        "user",
                        message
                    )

                    # No se genera ninguna respuesta.
                    return ""

            # ================================================
            # MEMORIA (save/update/delete)
            # ================================================

            if tool_name in [
                "save_memory",
                "update_memory",
                "delete_memory"
            ]:

                category = arguments.get(
                    "category",
                    "Datos Personales"
                )

                if result == "NEED_CONFIRM":

                    content = arguments.get(
                        "content",
                        ""
                    )

                    _set_pending_confirm(
                        category,
                        content
                    )

                elif result.startswith(
                    "SECRET_SAVED"
                ):

                    print(
                        "Dato sensible cifrado guardado."
                    )

                elif result.startswith("OK"):

                    if tool_name == "save_memory":
                        print(
                            f"Memoria guardada: {category}."
                        )
                    elif tool_name == "update_memory":
                        print(
                            f"Memoria actualizada: {category}."
                        )
                    else:
                        print(
                            f"Memoria borrada: {category}."
                        )

                elif result.startswith(
                    "NOT_FOUND"
                ):

                    print(
                        "No encontré eso en la memoria."
                    )

            # ------------------------------------------------
            # TOOL NORMAL
            # ------------------------------------------------

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": result,
                }
            )


# ============================================================
# JARVIS STREAMING (tokens progresivos)
# ============================================================

# Marcador para notificaciones del sistema en la GUI.
# Cuando ask_jarvis_stream lo yield, la GUI lo muestra como
# mensaje [SYS] en lugar de como respuesta de JARVIS.
NOTICE_PREFIX = "__MEMNOTICE__:"

def ask_jarvis_stream(message: str):
    """
    Como ask_jarvis pero va devolviendo (yield) los trozos
    de texto según el modelo los genera, para mostrarlos
    en tiempo real en la interfaz.
    """

    # ========================================================
    # COMANDOS DIRECTOS
    # ========================================================

    direct_result = handle_direct_command(message)

    if direct_result is not None:

        save_message(
            SESSION_ID,
            "user",
            message
        )

        yield direct_result

        return

    # ========================================================
    # FASE 1 DE MEMORIA (reglas explícitas)
    # ========================================================

    memory_result, notice = handle_memory_commands(message)

    if notice:

        yield NOTICE_PREFIX + notice

    if memory_result is not None:

        yield memory_result

        return

    # ========================================================
    # MENSAJES
    # ========================================================

    messages = write_messages(message)

    # ========================================================
    # AGENT LOOP
    # ========================================================

    while True:

        content_parts = []

        for item in send_payload(messages, stream=True):

            if isinstance(item, str):
                # error de conexión / timeout
                yield item
                return

            message_chunk = item.get(
                "message",
                {}
            )

            piece = message_chunk.get("content")

            if piece:
                content_parts.append(piece)
                yield piece

            if item.get("done"):
                assistant_message = message_chunk
                break

        else:
            # el generador terminó sin done
            yield (
                "No he recibido respuesta de Ollama."
            )
            return

        messages.append(
            assistant_message
        )

        tool_calls = assistant_message.get(
            "tool_calls",
            []
        )

        if not tool_calls:

            answer = "".join(
                content_parts
            ).strip()

            # Eliminar emojis aunque Qwen los genere
            answer = remove_emojis(answer)

            save_message(
                SESSION_ID,
                "user",
                message
            )

            save_message(
                SESSION_ID,
                "assistant",
                answer
            )

            return

        for tool_call in tool_calls:

            function_data = (
                tool_call
                .get("function", {})
            )

            tool_name = function_data.get(
                "name"
            )

            arguments = function_data.get(
                "arguments",
                {}
            )

            print(
                f"Herramienta: {tool_name}"
            )

            print(
                f"Argumentos: {arguments}"
            )

            result = execute_tool(
                tool_name,
                arguments
            )

            print(
                f"Resultado: {result}"
            )

            if tool_name in [
                "open_program",
                "open_folder",
                "open_website"
            ]:

                if result == "OK":

                    save_message(
                        SESSION_ID,
                        "user",
                        message
                    )

                    # No se genera ninguna respuesta.
                    return ""

            # ================================================
            # MEMORIA (save/update/delete)
            # ================================================

            if tool_name in [
                "save_memory",
                "update_memory",
                "delete_memory"
            ]:

                category = arguments.get(
                    "category",
                    "Datos Personales"
                )

                if result == "NEED_CONFIRM":

                    # Guardar pendiente para confirmación
                    content = arguments.get(
                        "content",
                        ""
                    )

                    _set_pending_confirm(
                        category,
                        content
                    )

                elif result.startswith(
                    "SECRET_SAVED"
                ):

                    yield (
                        NOTICE_PREFIX
                        + "Dato sensible cifrado guardado."
                    )

                elif result.startswith("OK"):

                    if tool_name == "save_memory":
                        notice = (
                            "Memoria guardada: "
                            f"{category}."
                        )
                    elif tool_name == "update_memory":
                        notice = (
                            "Memoria actualizada: "
                            f"{category}."
                        )
                    else:
                        notice = (
                            "Memoria borrada: "
                            f"{category}."
                        )

                    yield NOTICE_PREFIX + notice

                elif result.startswith(
                    "NOT_FOUND"
                ):

                    yield (
                        NOTICE_PREFIX
                        + "No encontré eso en la memoria."
                    )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": result,
                }
            )