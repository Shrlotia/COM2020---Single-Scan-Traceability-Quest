# Simple data import tools
# use to added products data from the SimplifiedOFFData.json file to database
import argparse
import json
from pathlib import Path
from flask import current_app

from sstq.extensions import db
from sstq.models import Product

DEFAULT_JSONL = Path(__file__).with_name("SimplifiedOFFData.jsonl")

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

def import_products(jsonl_path: Path, update_existing: bool) -> None:
    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0

    with current_app.app_context():
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
    parser = argparse.ArgumentParser(
        description="Import code/product_name/brands/categories from SimplifiedOFFData.jsonl into products table."
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_JSONL),
        help="Path to OFF jsonl file (default: SimplifiedOFFData.jsonl in project root).",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing products with same barcode.",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.file)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"File not found: {jsonl_path}")

    import_products(jsonl_path, update_existing=args.update_existing)

if __name__ == "__main__":
    main()