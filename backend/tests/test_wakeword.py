import numpy as np
import sounddevice as sd
from openwakeword.model import Model

DEVICE = 1
SAMPLE_RATE = 16000
FRAME_SIZE = 1280

THRESHOLD = 0.5
RESET_THRESHOLD = 0.2

print("Cargando modelo...")

model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

print("Modelo cargado.")
print()
print("Micrófono:", sd.query_devices(DEVICE)["name"])
print()
print("🟢 Esperando 'Hey Jarvis'...")
print("Pulsa Ctrl+C para salir.")
print()

detected = False

try:
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        device=DEVICE,
        channels=1,
        dtype="int16"
    ) as stream:

        while True:
            audio, overflowed = stream.read(FRAME_SIZE)

            audio = np.asarray(audio[:, 0], dtype=np.int16)

            predictions = model.predict(audio)

            score = float(
                predictions.get("hey_jarvis", 0.0)
            )

            # Detectar wake word
            if not detected and score >= THRESHOLD:
                print()
                print(f"🔔 ¡HEY JARVIS DETECTADO! ({score:.2f})")
                print("🎤 Preparado para escuchar...")
                print()

                detected = True

            # Esperar a que termine la palabra
            if detected and score < RESET_THRESHOLD:
                detected = False

except KeyboardInterrupt:
    print()
    print("🛑 Detector detenido.")