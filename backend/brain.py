import re
import json
import requests

from obsidian import search_vault
from database import save_message, get_conversation

from system_tools import (
    AVAILABLE_FUNCTIONS,
    open_program,
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
]


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

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": result,
                }
            )