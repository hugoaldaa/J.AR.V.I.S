import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.memoria.database import init_database, save_message, get_conversation, DB_PATH


print("Inicializando base de datos...")

init_database()

print(f"Base de datos: {DB_PATH}")

save_message(
    "test-session",
    "user",
    "Hola Jarvis"
)

save_message(
    "test-session",
    "assistant",
    "Hola. Soy Jarvis."
)

print()
print("Mensajes guardados:")
print()

messages = get_conversation("test-session")

for role, content, created_at in messages:
    print(f"[{created_at}] {role}: {content}")

print()
print("SQLite funciona correctamente.")