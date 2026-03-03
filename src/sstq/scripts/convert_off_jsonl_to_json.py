import json
from pathlib import Path
from typing import Any, Dict, List


def main() -> None:
    """
    Convert the existing line-delimited JSON file
    at COM2020---Single-Scan-Traceability-Quest/src/instance/SimplifiedOFFData.jsonl
    into a JSON array at data/SimplifiedOFFData.json (as expected by fetch_off_images.py).
    """
    base_dir = Path(__file__).resolve().parent

    jsonl_path = (
        base_dir
        / "COM2020---Single-Scan-Traceability-Quest"
        / "src"
        / "instance"
        / "SimplifiedOFFData.jsonl"
    )

    if not jsonl_path.is_file():
        print(f"Source JSONL file not found: {jsonl_path}")
        return

    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_array_path = data_dir / "SimplifiedOFFData.json"

    products: List[Dict[str, Any]] = []

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    products.append(obj)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    with json_array_path.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(products)} products to {json_array_path}")


if __name__ == "__main__":
    main()

