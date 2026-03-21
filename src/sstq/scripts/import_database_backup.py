"""Import a JSONL backup file and overwrite the current SQLite database.

Usage:
  PYTHONPATH=src python3 src/sstq/scripts/import_database_backup.py --file src/instance/backup/20260321-120000.jsonl
"""

import argparse
import json
import sqlite3
from pathlib import Path

from sstq import create_app
from sstq.extensions import db


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INSTANCE_DIR = PROJECT_ROOT / "src" / "instance"
BACKUP_DIR = INSTANCE_DIR / "backup"
DB_PATH = INSTANCE_DIR / "trace_quest.db"

TABLE_ORDER = [
    "users",
    "players",
    "products",
    "stages",
    "breakdowns",
    "claims",
    "evidence",
    "issues",
    "missions",
    "badges",
    "changelogs",
]


def resolve_backup_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate

    search_paths = [
        Path.cwd() / candidate,
        BACKUP_DIR / candidate,
        INSTANCE_DIR / candidate,
        PROJECT_ROOT / candidate,
    ]
    for path in search_paths:
        if path.exists():
            return path
    return candidate


def load_rows(backup_path: Path) -> dict[str, list[dict]]:
    rows_by_table: dict[str, list[dict]] = {}
    with backup_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            rows_by_table.setdefault(item["table"], []).append(item["row"])
    return rows_by_table


def insert_rows(conn: sqlite3.Connection, table_name: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    values = [[row.get(column) for column in columns] for row in rows]
    conn.executemany(
        f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
        values,
    )
    return len(rows)


def restore_backup(backup_path: Path) -> None:
    rows_by_table = load_rows(backup_path)

    if DB_PATH.exists():
        DB_PATH.unlink()

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")

    restored = 0
    for table_name in TABLE_ORDER:
        rows = rows_by_table.get(table_name, [])
        restored += insert_rows(conn, table_name, rows)

    for table_name, rows in rows_by_table.items():
        if table_name in TABLE_ORDER:
            continue
        restored += insert_rows(conn, table_name, rows)

    for table_name in rows_by_table:
        try:
            pk_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            pk_columns = [row[1] for row in pk_info if row[5]]
            if len(pk_columns) == 1:
                pk_name = pk_columns[0]
                max_pk = conn.execute(f"SELECT MAX({pk_name}) FROM {table_name}").fetchone()[0]
                if isinstance(max_pk, int):
                    conn.execute(
                        "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES(?, ?)",
                        (table_name, max_pk),
                    )
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    print(f"Imported {restored} rows from {backup_path} into {DB_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a backup JSONL file and overwrite the current SQLite database.")
    parser.add_argument("--file", required=True, help="Path to the backup JSONL file.")
    args = parser.parse_args()

    backup_path = resolve_backup_path(args.file)
    if not backup_path.exists():
        raise SystemExit(f"Backup file not found: {backup_path}")

    restore_backup(backup_path)


if __name__ == "__main__":
    main()
