import sqlite3
import json
from pathlib import Path

from cryptography.fernet import Fernet


# Ruta de la base de datos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jarvis.db"

CONFIG_PATH = Path(__file__).resolve().parent / "memory_config.json"

DEFAULT_KEY_FILE = ".jarvis_memoria.key"


def _load_key_filename():
    """
    Lee el nombre del archivo de clave del config.
    """

    try:

        with open(
            CONFIG_PATH,
            encoding="utf-8"
        ) as file:

            config = json.load(file)

        return config.get(
            "clave_secrets",
            DEFAULT_KEY_FILE
        )

    except Exception:

        return DEFAULT_KEY_FILE


def _get_or_create_key() -> bytes:
    """
    Obtiene la clave Fernet para cifrar los secretos.
    La genera y guarda en data/ si no existe.
    """

    key_name = _load_key_filename()

    key_path = DATA_DIR / key_name

    if key_path.exists():

        return key_path.read_bytes()

    # Generar nueva clave
    key = Fernet.generate_key()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    key_path.write_bytes(key)

    # Restringir permisos en Windows (solo lectura/escritura
    # para el usuario actual).
    try:
        import os
        os.chmod(key_path, 0o600)
    except Exception:
        pass

    return key


def _get_fernet():
    return Fernet(_get_or_create_key())


def encrypt_secret(plaintext: str) -> bytes:
    return _get_fernet().encrypt(
        plaintext.encode("utf-8")
    )


def decrypt_secret(token: bytes) -> str:
    return _get_fernet().decrypt(
        token
    ).decode("utf-8")


def get_connection():
    """
    Abre una conexión con la base de datos.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    return connection


def init_database():
    """
    Crea las tablas necesarias si todavía no existen.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # Historial de conversaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Acciones que Jarvis realice en el futuro
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            parameters TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tareas de Jarvis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Datos sensibles cifrados (con contraseñas, DNI, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT UNIQUE NOT NULL,
            encrypted_data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def save_message(session_id: str, role: str, content: str):
    """
    Guarda un mensaje en el historial.
    
    role puede ser:
    - user
    - assistant
    - system
    """

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO conversations
        (session_id, role, content)
        VALUES (?, ?, ?)
        """,
        (session_id, role, content)
    )

    connection.commit()
    connection.close()


def get_conversation(session_id: str, limit: int = 20):
    """
    Recupera los últimos mensajes de una conversación.
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT role, content, created_at
        FROM conversations
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit)
    )

    messages = cursor.fetchall()

    connection.close()

    # Los devolvemos en orden cronológico
    messages.reverse()

    return messages


# ============================================================
# SECRETOS CIFRADOS
# ============================================================

def save_secret(label: str, plaintext: str) -> str:
    """
    Guarda un dato sensible cifrado en la base de datos.

    Devuelve "saved" o "updated" según si ya existía.
    """

    token = encrypt_secret(plaintext)

    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT id FROM secrets
        WHERE label = ?
        """,
        (label,)
    )

    existing = cursor.fetchone()

    if existing:

        connection.execute(
            """
            UPDATE secrets
            SET encrypted_data = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE label = ?
            """,
            (token, label)
        )

        connection.commit()
        connection.close()

        return "updated"

    connection.execute(
        """
        INSERT INTO secrets (label, encrypted_data)
        VALUES (?, ?)
        """,
        (label, token)
    )

    connection.commit()
    connection.close()

    return "saved"


def get_secret(label: str):
    """
    Recupera y descifra un dato sensible.

    Devuelve el texto plano o None si no existe.
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT encrypted_data FROM secrets
        WHERE label = ?
        """,
        (label,)
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    try:

        return decrypt_secret(row[0])

    except Exception:

        return None


def has_secret(label: str) -> bool:
    """
    Comprueba si existe un secreto con esa etiqueta,
    sin descifrarlo.
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT 1 FROM secrets WHERE label = ?
        """,
        (label,)
    )

    exists = cursor.fetchone() is not None

    connection.close()

    return exists


def delete_secret(label: str) -> str:
    """
    Borra un dato sensible cifrado.

    Devuelve "deleted" o "not_found".
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        DELETE FROM secrets WHERE label = ?
        """,
        (label,)
    )

    connection.commit()

    deleted = cursor.rowcount > 0

    connection.close()

    if deleted:
        return "deleted"

    return "not_found"