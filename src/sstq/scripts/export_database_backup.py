"""Export the whole SQLite database into a timestamped JSONL backup.

Usage:
  PYTHONPATH=src python3 src/sstq/scripts/export_database_backup.py
  PYTHONPATH=src python3 src/sstq/scripts/export_database_backup.py --output src/instance/backup/20260321-120000.jsonl
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INSTANCE_DIR = PROJECT_ROOT / "src" / "instance"
BACKUP_DIR = INSTANCE_DIR / "backup"
DB_PATH = INSTANCE_DIR / "trace_quest.db"


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return BACKUP_DIR / f"{timestamp}.jsonl"


def export_database(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    table_names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]

    exported = 0
    with output_path.open("w", encoding="utf-8") as fh:
        for table_name in table_names:
            for row in conn.execute(f"SELECT * FROM {table_name}"):
                fh.write(json.dumps({"table": table_name, "row": dict(row)}, ensure_ascii=False) + "\n")
                exported += 1

    conn.close()
    print(f"Exported {exported} rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the whole SQLite database into a timestamped JSONL backup.")
    parser.add_argument("--output", help="Optional output path for the backup JSONL file.")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser() if args.output else default_output_path()
    export_database(output_path)


if __name__ == "__main__":
    main()
