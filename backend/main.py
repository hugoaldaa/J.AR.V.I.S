import threading
import queue
import time
import sounddevice as sd

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from brain import ask_jarvis
from tts import speak

from voice import (
    wait_for_wake_word,
    listen_command,
    wake_model,
    DEVICE,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

STOP_EVENT = threading.Event()

command_queue = queue.Queue()

TTS_LOCK = threading.Lock()


# ============================================================
# TTS
# ============================================================

def jarvis_speak(text):
    """
    Hace hablar a Jarvis.
    Evita que dos respuestas se reproduzcan simultáneamente.
    """

    with TTS_LOCK:
        speak(text)


# ============================================================
# PROCESAR COMANDOS
# ============================================================

def process_command(command, source):

    command = command.strip()

    if not command:
        return


    # --------------------------------------------------------
    # SALIR
    # --------------------------------------------------------

    if command.lower() in ["salir", "exit", "quit"]:

        print()
        print("🛑 Cerrando Jarvis...")

        STOP_EVENT.set()

        jarvis_speak("Hasta luego.")

        return


    # --------------------------------------------------------
    # MOSTRAR ORDEN
    # --------------------------------------------------------

    print()
    print("─" * 60)

    if source == "voice":
        print("🎤 ORDEN POR VOZ")
    else:
        print("⌨️ ORDEN POR TERMINAL")

    print("─" * 60)

    print()
    print("📝 Tú:", command)
    print()


    # --------------------------------------------------------
    # QWEN
    # --------------------------------------------------------

    print("🤖 Jarvis está pensando...")

    try:

        answer = ask_jarvis(command)

    except Exception as e:

        print()
        print(f"❌ Error con Qwen/Ollama: {e}")
        print()

        return


    # --------------------------------------------------------
    # RESPUESTA
    # --------------------------------------------------------

    if answer:
        print()
        print("Jarvis:", answer)
        print()
    
        jarvis_speak(answer)
    
        print()


# ============================================================
# PROCESADOR
# ============================================================

def processor_loop():

    while not STOP_EVENT.is_set():

        try:

            source, command = command_queue.get(
                timeout=0.5
            )

        except queue.Empty:

            continue


        try:

            process_command(
                command,
                source
            )

        finally:

            command_queue.task_done()


# ============================================================
# TERMINAL
# ============================================================

def terminal_loop():

    session = PromptSession()

    while not STOP_EVENT.is_set():

        try:

            # ------------------------------------------------
            # patch_stdout hace que los mensajes de otros
            # hilos aparezcan ARRIBA del prompt.
            # ------------------------------------------------

            with patch_stdout():

                command = session.prompt(
                    "Tú: "
                )

        except (KeyboardInterrupt, EOFError):

            print()
            print("🛑 Cerrando Jarvis...")

            STOP_EVENT.set()

            break


        command = command.strip()

        if not command:
            continue


        # ------------------------------------------------
        # ENVIAR A LA COLA
        # ------------------------------------------------

        command_queue.put(
            ("terminal", command)
        )


# ============================================================
# VOZ
# ============================================================

def voice_loop():

    print()
    print("🎤 VOZ ACTIVADA")
    print("Di 'Hey Jarvis' para despertar a Jarvis.")
    print()

    while not STOP_EVENT.is_set():

        try:

            # ------------------------------------------------
            # ESPERAR WAKE WORD
            # ------------------------------------------------

            score = wait_for_wake_word(
                STOP_EVENT
            )

            if STOP_EVENT.is_set():
                break

            if score is None:
                continue


            print()
            print(
                f"🔔 HEY JARVIS DETECTADO "
                f"({score:.2f})"
            )


            # ------------------------------------------------
            # RESPUESTA DE JARVIS
            # ------------------------------------------------

            print(
                "🔊 Jarvis: ¿Qué quieres?"
            )

            jarvis_speak(
                "¿Qué quieres?"
            )


            if STOP_EVENT.is_set():
                break


            # ------------------------------------------------
            # ESCUCHAR ORDEN
            # ------------------------------------------------

            command = listen_command(
                STOP_EVENT
            )


            # ------------------------------------------------
            # ENVIAR A LA COLA
            # ------------------------------------------------

            if command:

                print()
                print(
                    "📝 Orden detectada por voz:",
                    command
                )

                command_queue.put(
                    ("voice", command)
                )

            else:

                print()
                print(
                    "⚠️ No he entendido "
                    "ninguna orden."
                )


            # ------------------------------------------------
            # RESET WAKE WORD
            # ------------------------------------------------

            try:

                wake_model.reset()

            except Exception:

                pass


            if not STOP_EVENT.is_set():

                print()
                print(
                    "🟢 Esperando "
                    "'Hey Jarvis'..."
                )
                print()


        except Exception as e:

            print()
            print(
                f"❌ Error en el sistema "
                f"de voz: {e}"
            )

            time.sleep(1)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("                    J.A.R.V.I.S")
    print("=" * 60)
    print()

    print("Sistema iniciado.")
    print()


    # --------------------------------------------------------
    # MICRÓFONO
    # --------------------------------------------------------

    try:

        microphone_name = sd.query_devices(
            DEVICE
        )["name"]

        print("🎤 Micrófono:")
        print(f"   {microphone_name}")

    except Exception:

        print(
            f"🎤 Micrófono: dispositivo {DEVICE}"
        )


    print()

    print("🎤 Voz:")
    print("   Di 'Hey Jarvis'")

    print()

    print("⌨️ Terminal:")
    print("   Escribe directamente")

    print()

    print("🛑 Salir:")
    print("   Escribe 'salir'")

    print()

    print("=" * 60)
    print()


    # ========================================================
    # CREAR HILOS
    # ========================================================

    processor_thread = threading.Thread(
        target=processor_loop,
        name="JarvisProcessor",
        daemon=True
    )

    voice_thread = threading.Thread(
        target=voice_loop,
        name="JarvisVoice",
        daemon=True
    )

    terminal_thread = threading.Thread(
        target=terminal_loop,
        name="JarvisTerminal",
        daemon=True
    )


    # ========================================================
    # INICIAR
    # ========================================================

    processor_thread.start()

    voice_thread.start()

    terminal_thread.start()


    # ========================================================
    # ESPERAR
    # ========================================================

    try:

        while not STOP_EVENT.is_set():

            time.sleep(0.5)

    except KeyboardInterrupt:

        print()
        print("🛑 Interrupción detectada.")

        STOP_EVENT.set()


    # ========================================================
    # CIERRE
    # ========================================================

    STOP_EVENT.set()

    print()
    print("⏳ Cerrando Jarvis...")


    voice_thread.join(
        timeout=2
    )

    terminal_thread.join(
        timeout=2
    )

    processor_thread.join(
        timeout=2
    )


    print()
    print("=" * 60)
    print("                 JARVIS CERRADO")
    print("=" * 60)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()