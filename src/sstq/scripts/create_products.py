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

  python ./src/sstq/scripts/create_products.py --file src/instance/Electronics_with_codes.jsonl --file src/instance/luxury_clothing_with_codes.jsonl
    - Import multiple JSONL sources in one run.

  python ./src/sstq/scripts/create_products.py --file src/instance/new_products.jsonl --update-existing
    - Update existing products with the same barcode.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from sstq import create_app
from sstq.extensions import db
from sstq.models import Product

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INSTANCE_DIR_CANDIDATES = [
    PROJECT_ROOT / "instance",
    PROJECT_ROOT / "src" / "instance",
]
LEGACY_DEFAULT_JSONL = Path(__file__).with_name("SimplifiedOFFData.jsonl")
DEFAULT_SOURCE_FILES = [
    "SimplifiedOFFData.jsonl",
    "Electronics_with_codes.jsonl",
    "luxury_clothing_with_codes.jsonl",
]


def get_default_jsonl_paths() -> list[Path]:
    paths = []
    for filename in DEFAULT_SOURCE_FILES:
        resolved = None
        for instance_dir in INSTANCE_DIR_CANDIDATES:
            candidate = instance_dir / filename
            if candidate.exists():
                resolved = candidate
                break

        if resolved:
            paths.append(resolved)
        elif filename == "SimplifiedOFFData.jsonl" and LEGACY_DEFAULT_JSONL.exists():
            paths.append(LEGACY_DEFAULT_JSONL)

    return paths or [INSTANCE_DIR_CANDIDATES[0] / DEFAULT_SOURCE_FILES[0]]


def get_source_name(jsonl_path: Path, item: dict[str, Any]) -> str:
    name = jsonl_path.name.lower()
    if "electronics_with_codes" in name:
        return "electronics"
    if "luxury_clothing_with_codes" in name:
        return "luxury_clothing"
    if "product_name" in item:
        return "simplified_off"
    if {"main_category", "sub_category", "link"} & item.keys():
        return "electronics"
    if {"primary_category", "category_1", "availability"} & item.keys():
        return "luxury_clothing"
    return "generic"

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


def compact_parts(parts: list[str]) -> list[str]:
    seen = set()
    result = []
    for part in parts:
        text = str(part or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def infer_brand_from_name(name: str) -> str:
    words = [word.strip(" ,.-()") for word in str(name or "").split()]
    if not words:
        return "Unknown Brand"

    if len(words) >= 2 and words[0].lower() == "hp" and words[1].isalnum():
        return "HP"

    first = words[0]
    if first and any(ch.isalpha() for ch in first):
        return first[:128]
    return "Unknown Brand"


def build_description(parts: list[str], fallback: str) -> str:
    description = " | ".join(compact_parts(parts))
    return normalize_text(description, fallback, 512)


def map_record(item: dict[str, Any], line_no: int, source_name: str) -> dict[str, Any] | None:
    barcode = normalize_barcode(item.get("code", ""))
    if not barcode:
        return None

    if source_name == "simplified_off":
        name = normalize_text(item.get("product_name"), "Unknown Product", 128)
        brand = normalize_text(item.get("brands"), "Unknown Brand", 128)
        category = normalize_text(item.get("categories"), "Uncategorized", 128)
        description = normalize_text(
            f"Imported from SimplifiedOFFData (line {line_no})",
            "Imported product data.",
            512,
        )
        image = None
    elif source_name == "electronics":
        name = normalize_text(item.get("name"), "Unknown Product", 128)
        brand = normalize_text(item.get("brand"), infer_brand_from_name(name), 128)
        category = normalize_text(
            compact_parts([item.get("main_category"), item.get("sub_category")]),
            "Electronics",
            128,
        )
        description = build_description(
            [
                item.get("material"),
                f"Made in {item.get('country_of_manufacture')}" if item.get("country_of_manufacture") else "",
                f"Rating {item.get('ratings')}/5 from {item.get('no_of_ratings')} reviews"
                if item.get("ratings") and item.get("no_of_ratings")
                else "",
                item.get("link"),
            ],
            f"Imported electronics product (line {line_no}).",
        )
        image = normalize_text(item.get("image"), "", 256) or None
    elif source_name == "luxury_clothing":
        availability = str(item.get("availability") or "").strip().lower()
        price = item.get("price")
        if availability == "discontinued":
            return None
        if isinstance(price, (int, float)) and price <= 0:
            return None

        name = normalize_text(item.get("name"), "Unknown Product", 128)
        brand = normalize_text(item.get("brand"), infer_brand_from_name(name), 128)
        category = normalize_text(
            compact_parts([item.get("primary_category"), item.get("category_1")]),
            "Luxury Clothing",
            128,
        )
        description = build_description(
            [
                item.get("description"),
                item.get("material"),
                f"Color: {item.get('color')}" if item.get("color") else "",
                f"Made in {item.get('country_of_manufacture')}" if item.get("country_of_manufacture") else "",
                f"Price: {item.get('currency')} {price:g}" if isinstance(price, (int, float)) and item.get("currency") else "",
                f"Rating {item.get('average_rating')}/5 from {item.get('reviews_count')} reviews"
                if item.get("average_rating") and item.get("reviews_count")
                else "",
                item.get("url"),
            ],
            f"Imported luxury product (line {line_no}).",
        )
        image = None
    else:
        name = normalize_text(item.get("name") or item.get("product_name"), "Unknown Product", 128)
        brand = normalize_text(item.get("brand") or item.get("brands"), infer_brand_from_name(name), 128)
        category = normalize_text(
            item.get("category")
            or item.get("categories")
            or item.get("main_category")
            or item.get("primary_category"),
            "Uncategorized",
            128,
        )
        description = build_description(
            [
                item.get("description"),
                item.get("material"),
                item.get("link") or item.get("url"),
            ],
            f"Imported product data (line {line_no}).",
        )
        image = normalize_text(item.get("image"), "", 256) or None

    return {
        "barcode": barcode,
        "name": name,
        "brand": brand,
        "category": category,
        "description": description,
        "image": image,
    }


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


def import_products(jsonl_paths: list[Path], update_existing: bool) -> None:
    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0

    app = create_app()
    with app.app_context():
        db.create_all()

        for jsonl_path in jsonl_paths:
            with jsonl_path.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        invalid += 1
                        continue

                    mapped = map_record(item, line_no, get_source_name(jsonl_path, item))
                    if not mapped:
                        invalid += 1
                        continue

                    existing = db.session.get(Product, mapped["barcode"])
                    if existing:
                        if not update_existing:
                            skipped += 1
                            continue
                        existing.name = mapped["name"]
                        existing.brand = mapped["brand"]
                        existing.category = mapped["category"]
                        existing.description = mapped["description"]
                        existing.image = mapped["image"]
                        updated += 1
                    else:
                        db.session.add(Product(**mapped))
                        inserted += 1

                    if (inserted + updated) % 500 == 0:
                        db.session.commit()

        db.session.commit()

    print(f"Done. inserted={inserted}, updated={updated}, skipped={skipped}, invalid={invalid}")

def main() -> None:
    default_files = get_default_jsonl_paths()
    parser = argparse.ArgumentParser(
        description="Import product records from one or more JSONL files into the products table."
    )
    parser.add_argument(
        "--file",
        action="append",
        default=None,
        help=(
            "Path to a JSONL file. Can be repeated. Relative path lookup order: current dir -> "
            "instance/ -> project root -> scripts/. Default imports known files from src/instance."
        ),
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing products with same barcode.",
    )
    args = parser.parse_args()

    jsonl_paths = [resolve_jsonl_path(path) for path in (args.file or [str(path) for path in default_files])]
    missing_paths = [path for path in jsonl_paths if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"File not found: {missing_text}")

    import_products(jsonl_paths, update_existing=args.update_existing)

if __name__ == "__main__":
    main()
