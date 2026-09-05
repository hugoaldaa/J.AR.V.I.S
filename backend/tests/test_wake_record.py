import numpy as np
import sounddevice as sd
from openwakeword.model import Model
import wave

DEVICE = 1
SAMPLE_RATE = 16000
SECONDS = 3

print("Cargando modelo...")

model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

print("Modelo cargado.")
print()
print("🎤 Vas a grabar 3 segundos.")
print('Di claramente: "HEY JARVIS"')
print()

input("Pulsa ENTER para empezar...")

print("🔴 GRABANDO...")

audio = sd.rec(
    int(SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    device=DEVICE
)

sd.wait()

print("🟢 Grabación terminada.")

audio = np.asarray(audio[:, 0], dtype=np.int16)

# Guardar grabación
with wave.open("wake_test.wav", "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(audio.tobytes())

print()
print("Analizando...")

# Analizar en bloques de 1280 muestras
scores = []

for i in range(0, len(audio) - 1280, 1280):
    frame = audio[i:i + 1280]

    prediction = model.predict(frame)

    score = float(prediction.get("hey_jarvis", 0.0))
    scores.append(score)

    print(f"Score: {score:.4f}")

print()
print("================================")
print(f"MEJOR SCORE: {max(scores):.4f}")
print("================================")
print()
print("Grabación guardada como:")
print("wake_test.wav")