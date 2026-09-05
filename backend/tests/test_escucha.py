import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel


DEVICE = 1
SAMPLE_RATE = 16000
SECONDS = 5


print("Cargando Whisper...")
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("Whisper cargado.")
print()
print("🎤 Habla durante 5 segundos...")
print("Di algo como: Hola Jarvis, ¿cómo estás?")

audio = sd.rec(
    int(SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=DEVICE
)

sd.wait()

print()
print("🔄 Transcribiendo...")

audio = np.squeeze(audio)

segments, info = model.transcribe(
    audio,
    language="es",
    vad_filter=True
)

text = " ".join(segment.text for segment in segments).strip()

print()
print("📝 Texto detectado:")
print(text)