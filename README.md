# J.A.R.V.I.S

Asistente personal local para Windows inspirado en JARVIS (Iron Man). Funciona por **voz y por texto**, con un modelo de lenguaje ejecutado en local (Ollama + Qwen3 8B), memoria persistente, herramientas del sistema y una interfaz gráfica holográfica.

Todo el procesamiento ocurre en tu ordenador: no se envían conversaciones a servicios externos (salvo consultas puntuales como el tiempo meteorológico).

---

## Características

- 🎤 **Activación por voz** con la wake word *"Hey Jarvis"* (openwakeword).
- 🗣️ **Reconocimiento de voz** en español con faster-whisper (modelo `small`, CPU int8, filtro VAD).
- 🔊 **Respuesta hablada** mediante TTS de Windows (SAPI5 / pyttsx3).
- 🧠 **Cerebro local**: Qwen3 8B vía Ollama, con *tool calling* (bucle de agente) y respuestas en streaming.
- 💾 **Memoria doble**:
  - Historial de conversaciones en SQLite.
  - Memoria permanente en notas Markdown de Obsidian, con guardado automático y comandos explícitos.
- 🔐 **Datos sensibles cifrados** (Fernet) en SQLite, con confirmación previa del usuario.
- 🛠️ **Herramientas del sistema**: hora, fecha, info del PC, abrir programas/carpetas/webs, meteorología.
- 🖥️ **Interfaz holográfica** en PySide6 con esfera animada que cambia de color según el estado.
- ⌨️ **Modo terminal** alternativo con entrada de texto y voz simultáneas.

---

## Cómo funciona

```
"Hey Jarvis" ──► openwakeword (detección)
                      │
                      ▼
               Grabación de la orden (corta por silencio)
                      │
                      ▼
               faster-whisper (transcripción a texto)
                      │
                      ▼
               brain.py ──► Ollama / Qwen3 8B
                      │         │
                      │         ├──► Herramientas del sistema
                      │         └──► Memoria (Obsidian / SQLite)
                      ▼
               Respuesta en streaming ──► GUI / terminal
                      │
                      ▼
               TTS (SAPI5) ──► Jarvis habla
```

Mientras Jarvis habla, la escucha se pausa para no oírse a sí mismo.

### Estados de la interfaz

| Estado | Color | Significado |
|---|---|---|
| `WAITING` | Cian | Esperando "Hey Jarvis" |
| `LISTENING` | Verde | Grabando tu orden |
| `PROCESSING` | Ámbar | Pensando / ejecutando herramientas |
| `SPEAKING` | Violeta | Hablando |

---

## Estructura del proyecto

```
J.A.R.V.I.S/
├── backend/
│   ├── gui.py              # Interfaz holográfica PySide6 (punto de entrada principal)
│   ├── gui_backup.py       # Versión anterior de la GUI (respaldo)
│   ├── main.py             # Modo terminal: voz + texto en hilos con cola de comandos
│   ├── brain.py            # Cerebro: prompt, agente con tools, streaming, memoria
│   ├── voice.py            # Wake word (openwakeword) + transcripción (faster-whisper)
│   ├── tts.py              # Síntesis de voz (pyttsx3 / SAPI5)
│   ├── database.py         # SQLite: conversaciones, acciones, tareas, secretos cifrados
│   ├── obsidian.py         # Búsqueda y escritura de memoria en el vault Obsidian
│   ├── system_tools.py     # Herramientas: hora, sistema, abrir apps/webs, clima, memoria
│   ├── aplications.py      # Helpers antiguos de apertura de apps (legado)
│   ├── memory_config.json  # Configuración de categorías y reglas de memoria
│   └── tests/              # Pruebas de micrófono, wake word, audio y SQLite
├── Obsidian/               # Vault de memoria (notas Markdown)
│   ├── 00 - Jarvis/        # Identidad, personalidad, reglas y voz del asistente
│   └── 01 - Memoria/       # Datos del usuario (Datos Personales, Preferencias, ...)
├── data/                   # Generado en ejecución (ignorado por git)
│   ├── jarvis.db           # Base de datos SQLite
│   └── .jarvis_memoria.key # Clave Fernet para los secretos cifrados
├── venv/                   # Entorno virtual de Python (ignorado por git)
├── requirements.txt        # Dependencias
└── start.ps1               # Arranca la GUI con el entorno virtual
```

---

## Requisitos

- **Windows** (usa SAPI5, `os.startfile` y rutas de Windows).
- **Python 3.13**.
- **[Ollama](https://ollama.com)** instalado y en ejecución, con el modelo:
  ```powershell
  ollama pull qwen3:8b
  ```
- **Micrófono** (para el modo voz).
- Conexión a internet solo para: descargar modelos la primera vez (Whisper) y consultar el clima (wttr.in).

## Instalación

```powershell
# 1. Clonar el repositorio
git clone https://github.com/hugoaldaa/J.AR.V.I.S.git
cd J.A.R.V.I.S

# 2. Crear el entorno virtual e instalar dependencias
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Asegurarse de que Ollama está iniciado y tiene el modelo
ollama pull qwen3:8b
```

> En el primer arranque, faster-whisper descarga el modelo `small` (~460 MB) automáticamente.

## Uso

### Interfaz gráfica (recomendado)

```powershell
.\start.ps1
```

> `start.ps1` tiene la ruta del proyecto fija (`D:\GITHUB\J.A.R.V.I.S`); ajústala si lo clonas en otra ubicación.

- Escribe en el campo inferior o di **"Hey Jarvis"** y espera a que te pregunte.
- Botón de voz para activar/desactivar la escucha.
- La esfera central muestra el estado en tiempo real; el chat muestra las respuestas token a token.

### Modo terminal

```powershell
.\venv\Scripts\Activate.ps1
cd backend
python main.py
```

- Escribe directamente o di "Hey Jarvis".
- Salir: escribe `salir`, `exit` o `quit` (o `Ctrl+C`).

---

## Memoria

### Memoria permanente (Obsidian)

Los datos del usuario se guardan como listas en notas Markdown dentro de `Obsidian/01 - Memoria/`, organizadas por categorías:

| Categoría | Archivo | Ejemplos |
|---|---|---|
| Datos Personales | `Datos Personales.md` | nombre, edad, cumpleaños, ciudad, email, profesión |
| Preferencias | `Preferencias.md` | gustos, favoritos |
| Planes y Tareas | `Planes y Tareas.md` | planes futuros, pendientes |
| Proyectos | `Proyectos.md` | proyectos del usuario |

Las categorías, sus reglas de detección y su sensibilidad se configuran en `backend/memory_config.json`.

**Tres formas de guardar:**

1. **Automática**: frases naturales como *"me llamo Ana"*, *"tengo 25 años"*, *"vivo en Madrid"*, *"me gusta el jazz"* se detectan con regex y se guardan (o actualizan) al instante.
2. **Comandos explícitos**: `recuerda`, `guarda`, `apunta` (guardar) y `olvida`, `borra`, `elimina` (borrar).
3. **Tool calling**: el modelo decide guardar/actualizar/borrar mediante las herramientas `save_memory`, `update_memory` y `delete_memory`.

En cada pregunta, las notas relevantes del vault se buscan por palabras clave y se inyectan en el contexto del modelo como *memoria permanente*.

### Datos sensibles

Contraseñas, PIN, DNI, tarjetas, IBAN, etc. **no se guardan en texto plano**:

1. Jarvis detecta la sensibilidad y pregunta: *"¿Quieres que lo guarde cifrado?"*.
2. Si confirmas, se cifra con **Fernet** y se guarda en la tabla `secrets` de SQLite.
3. La clave se genera automáticamente en `data/.jarvis_memoria.key` (nunca se sube a git).

### Historial (SQLite)

`data/jarvis.db` contiene:

- `conversations`: historial de mensajes (los últimos 20 se inyectan en cada petición).
- `actions`: registro de acciones realizadas.
- `tasks`: tareas.
- `secrets`: datos sensibles cifrados.

La base de datos y la clave se crean solas en el primer arranque.

---

## Herramientas del sistema

El modelo puede invocar estas herramientas (definidas en `system_tools.py`):

| Herramienta | Función |
|---|---|
| `get_time` | Hora actual del ordenador |
| `get_date` | Fecha actual en español |
| `get_system_info` | CPU, RAM y discos (psutil) |
| `open_program` | Abre programas de una lista permitida (Chrome, Edge, Firefox, VS Code, Obsidian, Discord, Spotify, Steam, calculadora, bloc de notas, explorador, terminal) |
| `open_folder` | Abre una carpeta de Windows |
| `open_website` | Abre una URL en el navegador predeterminado |
| `get_weather` | Tiempo actual de una ciudad (wttr.in, sin API key) |
| `save_memory` / `update_memory` / `delete_memory` | Gestión de la memoria permanente |

Además, órdenes directas como *"abre chrome"* se ejecutan sin pasar por el modelo (respuesta instantánea y silenciosa).

---

## Configuración

| Qué | Dónde | Valor por defecto |
|---|---|---|
| Modelo LLM | `brain.py` → `MODEL` | `qwen3:8b` |
| URL de Ollama | `brain.py` → `OLLAMA_URL` | `http://localhost:11434/api/chat` |
| Modelo en memoria | `brain.py` → `KEEP_ALIVE` | `12h` (evita recargas en frío) |
| Micrófono | `voice.py` → `DEVICE` | `1` (cámbialo según tu dispositivo) |
| Umbral wake word | `voice.py` → `WAKE_THRESHOLD` | `0.5` |
| Silencio para cortar | `voice.py` → `SILENCE_DURATION` | `2` s |
| Duración máxima de orden | `voice.py` → `MAX_LISTENING_TIME` | `15` s |
| Voz TTS | `tts.py` | SAPI5, velocidad 175, volumen 1.0 |
| Categorías y reglas de memoria | `backend/memory_config.json` | 4 categorías |

Para saber qué índice tiene tu micrófono:

```python
import sounddevice as sd
print(sd.query_devices())
```

---

## Tests

En `backend/tests/` hay utilidades de prueba:

- `test_microphone.py` / `test_audio_stream.py`: comprueba el micrófono.
- `test_wakeword.py` / `test_wake_record.py`: prueba la detección de "Hey Jarvis" (graba 3 s y muestra el score).
- `test_escucha.py`: prueba la escucha y transcripción.
- `testsqlite.py`: prueba la base de datos.

---

## Privacidad

- Las conversaciones, la memoria y los secretos viven **solo en tu ordenador** (`data/` y `Obsidian/01 - Memoria/`).
- `data/` y `venv/` están en `.gitignore`: la base de datos, la clave de cifrado y las grabaciones de audio **no se suben al repositorio**.
- El modelo se ejecuta en local con Ollama; no hay llamadas a APIs de pago ni envío de chats a la nube.
