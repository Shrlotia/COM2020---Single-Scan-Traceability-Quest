"""Bulk import product pictures from a local folder into the database.

Usage:
  python ./src/sstq/scripts/upload_picture.py
    - Read *.jpg/jpeg from script-local upload_picture folder first.
    - Rename files with the same rule as web upload: <barcode>-<random>.jpg
    - Save files into static/uploads/products and update Product.image.

  python ./src/sstq/scripts/upload_picture.py --source upload_picture
    - Use a specific source folder (relative or absolute path).

  python ./src/sstq/scripts/upload_picture.py --dry-run
    - Show what would be updated without writing files or database changes.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

from sstq import create_app
from sstq.extensions import db
from sstq.models import Product

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_CANDIDATES = [
    Path(__file__).resolve().parent / "upload_picture",
    PROJECT_ROOT / "upload_picture",
    PROJECT_ROOT / "src" / "upload_picture",
]


def normalize_barcode(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 12:
        return f"0{digits}"
    return digits


def resolve_source_dir(raw_path: str | None) -> Path:
    if raw_path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            return candidate
        lookups = [Path.cwd() / candidate, PROJECT_ROOT / candidate]
        for path in lookups:
            if path.exists():
                return path
        return candidate

    for candidate in DEFAULT_SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_SOURCE_CANDIDATES[0]


def find_product_by_filename_barcode(filename_barcode: str) -> Product | None:
    product = db.session.get(Product, filename_barcode)
    if product:
        return product

    normalized = normalize_barcode(filename_barcode)
    if normalized and normalized != filename_barcode:
        return db.session.get(Product, normalized)
    return None


def iter_image_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.jpg", "*.JPG", "*.jpeg", "*.JPEG"):
        files.extend(source_dir.glob(pattern))
    return sorted(set(files))


def import_pictures(source_dir: Path, dry_run: bool = False) -> None:
    app = create_app()
    copied = 0
    updated = 0
    missing_barcodes: list[str] = []

    with app.app_context():
        upload_dir = Path(app.static_folder) / "uploads" / "products"
        if not dry_run:
            upload_dir.mkdir(parents=True, exist_ok=True)

        image_files = iter_image_files(source_dir)
        if not image_files:
            print(f"No jpg/jpeg files found in: {source_dir}")
            return

        for image_path in image_files:
            filename_barcode = image_path.stem.strip()
            product = find_product_by_filename_barcode(filename_barcode)
            if not product:
                missing_barcodes.append(filename_barcode)
                continue

            safe_barcode = secure_filename(product.barcode) if product.barcode else "product"
            new_filename = f"{safe_barcode}-{uuid4().hex[:12]}.jpg"
            destination = upload_dir / new_filename
            image_url = f"/static/uploads/products/{new_filename}"

            if not dry_run:
                shutil.copy2(image_path, destination)
                copied += 1

            if product.image != image_url:
                product.image = image_url
                updated += 1

        if not dry_run:
            db.session.commit()

    total = len(iter_image_files(source_dir))
    mode = "DRY RUN" if dry_run else "Done"
    print(
        f"{mode}. scanned={total}, copied={copied}, "
        f"products_updated={updated}, missing={len(missing_barcodes)}"
    )
    if missing_barcodes:
        print("Missing Product.barcode for files:")
        for barcode in sorted(set(missing_barcodes)):
            print(f"- {barcode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import product pictures by matching filename barcode to Product.barcode."
    )
    parser.add_argument(
        "--source",
        help=(
            "Folder containing jpg/jpeg files named by barcode. "
            "Default: ./src/sstq/scripts/upload_picture/ (fallback: project upload_picture folders)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without copying files or writing database updates.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = resolve_source_dir(args.source)
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_dir}")

    import_pictures(source_dir=source_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
