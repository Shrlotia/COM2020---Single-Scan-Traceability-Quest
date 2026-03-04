"""Import product data from JSONL into the products table.

Usage:
  python ./src/sstq/scripts/create_products.py
    - Use default file search:
      1) ./instance/SimplifiedOFFData.jsonl
      2) ./src/instance/SimplifiedOFFData.jsonl
      3) ./src/sstq/scripts/SimplifiedOFFData.jsonl

  python ./src/sstq/scripts/create_products.py --file src/instance/new_products.jsonl
    - Import from a specific JSONL file.

  python ./src/sstq/scripts/create_products.py --file new_products.jsonl
    - Relative path works (current dir / instance / src/instance / project root / scripts).

  python ./src/sstq/scripts/create_products.py --file src/instance/new_products.jsonl --update-existing
    - Update existing products with the same barcode.
"""

import argparse
import json
from pathlib import Path

from sstq import create_app
from sstq.extensions import db
from sstq.models import Product

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INSTANCE_DIR_CANDIDATES = [
    PROJECT_ROOT / "instance",
    PROJECT_ROOT / "src" / "instance",
]
LEGACY_DEFAULT_JSONL = Path(__file__).with_name("SimplifiedOFFData.jsonl")


def get_default_jsonl_path() -> Path:
    for instance_dir in INSTANCE_DIR_CANDIDATES:
        candidate = instance_dir / "SimplifiedOFFData.jsonl"
        if candidate.exists():
            return candidate
    return INSTANCE_DIR_CANDIDATES[0] / "SimplifiedOFFData.jsonl"

def normalize_barcode(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 12:
        return f"0{digits}"
    return digits

def normalize_text(value, fallback: str, max_len: int) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value or "").strip()

    if not text:
        text = fallback
    return text[:max_len]

def resolve_jsonl_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate

    instance_paths = [instance_dir / candidate for instance_dir in INSTANCE_DIR_CANDIDATES]
    search_paths = [
        Path.cwd() / candidate,
        *instance_paths,
        PROJECT_ROOT / candidate,
        LEGACY_DEFAULT_JSONL.parent / candidate,
    ]
    for path in search_paths:
        if path.exists():
            return path
    return candidate


def import_products(jsonl_path: Path, update_existing: bool) -> None:
    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0

    app = create_app()
    with app.app_context():
        db.create_all()

        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    invalid += 1
                    continue

                barcode = normalize_barcode(item.get("code", ""))
                name = normalize_text(item.get("product_name"), "Unknown Product", 128)
                brand = normalize_text(item.get("brands"), "Unknown Brand", 128)
                category = normalize_text(item.get("categories"), "Uncategorized", 128)
                description = f"Imported from SimplifiedOFFData (line {line_no})"[:512]

                if not barcode:
                    invalid += 1
                    continue

                existing = db.session.get(Product, barcode)
                if existing:
                    if not update_existing:
                        skipped += 1
                        continue
                    existing.name = name
                    existing.brand = brand
                    existing.category = category
                    existing.description = description
                    updated += 1
                else:
                    db.session.add(
                        Product(
                            barcode=barcode,
                            name=name,
                            category=category,
                            brand=brand,
                            description=description,
                            image=None,
                        )
                    )
                    inserted += 1

                if (inserted + updated) % 500 == 0:
                    db.session.commit()

        db.session.commit()

    print(f"Done. inserted={inserted}, updated={updated}, skipped={skipped}, invalid={invalid}")

def main() -> None:
    default_file = get_default_jsonl_path()
    if not default_file.exists() and LEGACY_DEFAULT_JSONL.exists():
        default_file = LEGACY_DEFAULT_JSONL
    parser = argparse.ArgumentParser(
        description="Import code/product_name/brands/categories from SimplifiedOFFData.jsonl into products table."
    )
    parser.add_argument(
        "--file",
        default=str(default_file),
        help=(
            "Path to OFF jsonl file. Relative path lookup order: current dir -> instance/ -> "
            "project root -> scripts/. Default prefers instance/SimplifiedOFFData.jsonl."
        ),
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing products with same barcode.",
    )
    args = parser.parse_args()

    jsonl_path = resolve_jsonl_path(args.file)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"File not found: {jsonl_path}")

    import_products(jsonl_path, update_existing=args.update_existing)

if __name__ == "__main__":
    main()
