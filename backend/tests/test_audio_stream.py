import sounddevice as sd
import numpy as np

DEVICE = 1
SAMPLE_RATE = 16000
FRAME_SIZE = 1280

print("🎤 Abriendo micrófono...")
print(sd.query_devices(DEVICE)["name"])
print()

with sd.InputStream(
    device=DEVICE,
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    blocksize=FRAME_SIZE
) as stream:

    print("🟢 Micrófono activo.")
    print("Habla y mira los valores.")
    print("Ctrl+C para salir.")
    print()

    while True:
        audio, overflowed = stream.read(FRAME_SIZE)

        audio = np.asarray(audio[:, 0], dtype=np.int16)

        level = np.max(np.abs(audio))

        print(f"Nivel: {level:6d}", end="\r")