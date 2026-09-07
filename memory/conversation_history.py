"""
conversation_history.py
-----------------------
Persistent SQLite storage for Office Assistant chat history.

Each user question and its corresponding assistant answer are stored
as one history item.

Database:
    data/conversation_history.db
"""

import sqlite3
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "conversation_history.db"


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def get_connection():
    """
    Create and return a SQLite database connection.
    """

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return sqlite3.connect(DB_PATH)


# ---------------------------------------------------------------------------
# Initialize database
# ---------------------------------------------------------------------------

def initialize_database():
    """
    Create the history table if it does not already exist.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Save question and answer
# ---------------------------------------------------------------------------

def save_chat(question, answer):
    """
    Save one complete question-answer pair.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO chat_history
        (question, answer, created_at)
        VALUES (?, ?, ?)
        """,
        (
            question,
            answer,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    history_id = cursor.lastrowid

    conn.close()

    return history_id


# ---------------------------------------------------------------------------
# Get all history
# ---------------------------------------------------------------------------

def get_history():
    """
    Return all saved question-answer pairs.

    Newest questions appear first.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, question, answer, created_at
        FROM chat_history
        ORDER BY id DESC
        """
    )

    history = cursor.fetchall()

    conn.close()

    return history


# ---------------------------------------------------------------------------
# Get one history item
# ---------------------------------------------------------------------------

def get_chat(history_id):
    """
    Return one saved question-answer pair.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, question, answer, created_at
        FROM chat_history
        WHERE id = ?
        """,
        (history_id,)
    )

    chat = cursor.fetchone()

    conn.close()

    return chat


# ---------------------------------------------------------------------------
# Delete all history
# ---------------------------------------------------------------------------

def delete_all_history():
    """
    Delete all permanently stored history.

    This function is intentionally separate from Clear Conversation.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM chat_history
        """
    )

    conn.commit()
    conn.close()