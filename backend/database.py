import sqlite3
from pathlib import Path


# Ruta de la base de datos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jarvis.db"


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