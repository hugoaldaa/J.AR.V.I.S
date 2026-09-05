import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel


# ============================================================
# CONFIGURACIÓN
# ============================================================

DEVICE = 1
SAMPLE_RATE = 16000
FRAME_SIZE = 1280

WAKE_THRESHOLD = 0.5

# Tiempo que esperamos después de detectar "Hey Jarvis"
# para no grabar el wake word.
START_DELAY = 2

# Tiempo de silencio necesario para terminar una orden.
SILENCE_DURATION = 2

# Tiempo máximo que puede durar una orden.
MAX_LISTENING_TIME = 15

# Umbral de volumen del micrófono.
SILENCE_THRESHOLD = 500


# ============================================================
# CARGAR MODELOS
# ============================================================

print("Cargando wake word...")

wake_model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

print("Wake word cargado.")

print("Cargando Whisper...")

whisper_model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("Whisper cargado.")
print()


# ============================================================
# UTILIDADES
# ============================================================

def is_silence(audio):
    """
    Determina si el audio está por debajo
    del nivel mínimo considerado como voz.
    """

    level = np.max(np.abs(audio))

    return level < SILENCE_THRESHOLD


# ============================================================
# WAKE WORD
# ============================================================

def wait_for_wake_word(stop_event):
    """
    Espera hasta detectar "Hey Jarvis".

    Devuelve:
        float -> puntuación de detección
        None  -> si se ha detenido el sistema
    """

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        device=DEVICE,
        channels=1,
        dtype="int16"
    ) as stream:

        while not stop_event.is_set():

            audio, overflowed = stream.read(FRAME_SIZE)

            audio = np.asarray(
                audio[:, 0],
                dtype=np.int16
            )

            predictions = wake_model.predict(audio)

            score = float(
                predictions.get(
                    "hey_jarvis",
                    0.0
                )
            )

            if score >= WAKE_THRESHOLD:
                return score

    return None


# ============================================================
# ESCUCHAR ORDEN
# ============================================================

def listen_command(stop_event=None):
    """
    Escucha una orden después del wake word.

    La grabación termina cuando:
    - se detecta voz y después silencio suficiente
    - se alcanza MAX_LISTENING_TIME
    - se solicita detener el sistema

    Devuelve:
        str -> texto transcrito
        ""  -> si no se detectó ninguna orden
    """

    print()
    print("ESCUCHANDO...")
    print()

    audio_chunks = []

    silence_start = None
    start_time = time.time()
    speech_detected = False

    # Esperar antes de empezar a capturar la orden.
    time.sleep(START_DELAY)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        device=DEVICE,
        channels=1,
        dtype="int16"
    ) as stream:

        while True:

            # Permitir detener Jarvis desde la GUI.
            if stop_event is not None and stop_event.is_set():
                return ""

            audio, overflowed = stream.read(FRAME_SIZE)

            audio = np.asarray(
                audio[:, 0],
                dtype=np.int16
            )

            audio_chunks.append(audio.copy())

            # ------------------------------------------------
            # VOZ
            # ------------------------------------------------

            if not is_silence(audio):

                speech_detected = True
                silence_start = None

            # ------------------------------------------------
            # SILENCIO
            # ------------------------------------------------

            else:

                # Todavía no hemos empezado a hablar.
                if not speech_detected:

                    silence_start = None

                else:

                    if silence_start is None:
                        silence_start = time.time()

                    elif (
                        time.time() - silence_start
                        >= SILENCE_DURATION
                    ):
                        break

            # ------------------------------------------------
            # TIEMPO MÁXIMO
            # ------------------------------------------------

            if (
                time.time() - start_time
                >= MAX_LISTENING_TIME
            ):
                break

    if not audio_chunks:
        return ""

    # ========================================================
    # UNIR AUDIO
    # ========================================================

    audio = np.concatenate(audio_chunks)

    print()
    print("Fin de escucha.")
    print("Transcribiendo...")

    audio_float = (
        audio.astype(np.float32) / 32768.0
    )

    # ========================================================
    # WHISPER
    # ========================================================

    segments, info = whisper_model.transcribe(
        audio_float,
        language="es",
        vad_filter=True
    )

    text = " ".join(
        segment.text
        for segment in segments
    ).strip()

    return text