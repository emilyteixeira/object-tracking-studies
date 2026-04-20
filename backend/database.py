"""
SQLite persistence para passagens de caminhões.

Schema projetado para ser compatível com SQL Server (Guardian DB):
- TEXT para timestamps em ISO 8601 (equivale a NVARCHAR / DATETIME no SQL Server)
- INTEGER / REAL mapeiam direto para INT / FLOAT
- `synced_to_guardian`: flag 0/1 usada pelo script de sincronização futuro
"""

import sqlite3
import threading
from typing import Dict, List, Optional

from backend import config

# Lock global para serializar escritas (o detector roda em threads de executor)
_write_lock = threading.Lock()

_CREATE_PASSAGES = """
CREATE TABLE IF NOT EXISTS truck_passages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    truck_track_id      INTEGER NOT NULL,
    license_plate       TEXT,
    plate_confidence    REAL,
    max_speed_kmh       REAL,
    entry_time          TEXT NOT NULL,
    exit_time           TEXT,
    frame_path          TEXT,
    camera_id           TEXT DEFAULT 'cam01',
    synced_to_guardian  INTEGER DEFAULT 0
);
"""

_CREATE_PLATE_READS = """
CREATE TABLE IF NOT EXISTS plate_reads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    passage_id  INTEGER REFERENCES truck_passages(id),
    raw_text    TEXT,
    confidence  REAL,
    read_time   TEXT,
    frame_path  TEXT
);
"""


def init_db(path: str = config.DB_PATH) -> sqlite3.Connection:
    """Abre (ou cria) o banco e garante que as tabelas existem."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")   # escritas mais rápidas e seguras
    conn.execute(_CREATE_PASSAGES)
    conn.execute(_CREATE_PLATE_READS)
    conn.commit()
    return conn


def open_passage(
    conn: sqlite3.Connection,
    truck_track_id: int,
    entry_time: str,
    camera_id: str = config.CAMERA_ID,
) -> int:
    """Insere uma nova passagem e retorna o id gerado."""
    with _write_lock:
        cur = conn.execute(
            "INSERT INTO truck_passages (truck_track_id, entry_time, camera_id) "
            "VALUES (?, ?, ?)",
            (truck_track_id, entry_time, camera_id),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def close_passage(
    conn: sqlite3.Connection,
    passage_id: int,
    exit_time: str,
    max_speed_kmh: Optional[float],
    best_plate: Optional[str],
    plate_confidence: Optional[float],
    frame_path: Optional[str],
) -> None:
    """Atualiza a linha de passagem com dados coletados durante o cruzamento."""
    with _write_lock:
        conn.execute(
            """UPDATE truck_passages
               SET exit_time        = ?,
                   max_speed_kmh    = ?,
                   license_plate    = ?,
                   plate_confidence = ?,
                   frame_path       = ?
               WHERE id = ?""",
            (exit_time, max_speed_kmh, best_plate, plate_confidence, frame_path, passage_id),
        )
        conn.commit()


def add_plate_read(
    conn: sqlite3.Connection,
    passage_id: int,
    raw_text: str,
    confidence: float,
    read_time: str,
    frame_path: Optional[str] = None,
) -> None:
    """Registra uma leitura de placa (pode haver várias por passagem)."""
    with _write_lock:
        conn.execute(
            "INSERT INTO plate_reads (passage_id, raw_text, confidence, read_time, frame_path) "
            "VALUES (?, ?, ?, ?, ?)",
            (passage_id, raw_text, confidence, read_time, frame_path),
        )
        conn.commit()


def get_history(conn: sqlite3.Connection, limit: int = 100) -> List[Dict]:
    """Retorna as últimas `limit` passagens, mais recentes primeiro."""
    cur = conn.execute(
        """SELECT id, truck_track_id, license_plate, plate_confidence,
                  max_speed_kmh, entry_time, exit_time, frame_path, camera_id
           FROM truck_passages
           ORDER BY id DESC
           LIMIT ?""",
        (limit,),
    )
    return [dict(row) for row in cur.fetchall()]
