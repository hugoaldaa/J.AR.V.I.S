import sounddevice as sd

DEVICE = 1
SAMPLE_RATE = 16000
SECONDS = 5

print("🎤 Micrófono seleccionado:")
print(sd.query_devices(DEVICE)["name"])
print()
print("Habla durante 5 segundos...")

audio = sd.rec(
    int(SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=DEVICE
)

sd.wait()

print()
print("✅ Grabación terminada.")
print("Muestras grabadas:", len(audio))