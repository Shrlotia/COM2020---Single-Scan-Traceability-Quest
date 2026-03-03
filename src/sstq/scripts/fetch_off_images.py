import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


API_BASE_URL = "https://world.openfoodfacts.org/api/v2/product/{code}"
USER_AGENT = "Single-Scan-Traceability-Quest/1.0 (+https://world.openfoodfacts.org/)"
REQUEST_TIMEOUT = (5, 15)  # (connect, read) timeouts in seconds
MIN_IMAGE_SIZE_BYTES = 2 * 1024  # 2KB
API_DELAY_SECONDS = 0.15


def get_paths() -> Dict[str, Path]:
    """
    Resolve key paths relative to this script.

    Expected structure:
      - data/SimplifiedOFFData.json
      - assets/products/
    """
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    input_file = data_dir / "SimplifiedOFFData.json"
    output_file = data_dir / "SimplifiedOFFData_with_images.json"
    # Store images in the existing assets/products folder at project root
    assets_dir = base_dir / "assets" / "products"

    # Also mirror images into the Flask static directory so they can be served by the app
    static_assets_dir = (
        base_dir
        / "COM2020---Single-Scan-Traceability-Quest"
        / "src"
        / "sstq"
        / "static"
        / "assets"
        / "products"
    )
    return {
        "base_dir": base_dir,
        "data_dir": data_dir,
        "input_file": input_file,
        "output_file": output_file,
        "assets_dir": assets_dir,
        "static_assets_dir": static_assets_dir,
    }


def load_products(input_path: Path) -> List[Dict[str, Any]]:
    """
    Load product objects from the given JSON file.

    The file is expected to contain a JSON array of product objects.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_path}, got {type(data).__name__}")

    # Ensure each entry is a dict
    products: List[Dict[str, Any]] = []
    for idx, item in enumerate(data):
        if isinstance(item, dict):
            products.append(item)
        else:
            # Skip non-dict entries but keep script robust
            continue

    return products


def ensure_assets_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def image_file_is_valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > MIN_IMAGE_SIZE_BYTES
    except OSError:
        return False


def fetch_product_from_api(code: str, session: requests.Session) -> Dict[str, Any]:
    url = API_BASE_URL.format(code=code)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def download_image(url: str, dest_path: Path) -> bool:
    """
    Download an image to dest_path.

    Returns True if the image was downloaded and passes the size check.
    """
    # Ensure parent directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as r:
            r.raise_for_status()
            with dest_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    except Exception:
        # Clean up partial file if something went wrong
        if dest_path.exists():
            try:
                dest_path.unlink()
            except OSError:
                pass
        return False

    # Validate size
    if not image_file_is_valid(dest_path):
        try:
            dest_path.unlink()
        except OSError:
            pass
        return False

    return True


def _mirror_to_static(src: Path, static_dir: Path) -> None:
    """
    Copy the image at src into the Flask static assets directory so it can be served.
    """
    if not src.is_file():
        return

    static_dir.mkdir(parents=True, exist_ok=True)
    dest = static_dir / src.name
    try:
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
    except OSError:
        # If mirroring fails, we still keep the original asset; the app just might not show it.
        pass


def process_products(
    products: List[Dict[str, Any]],
    assets_dir: Path,
    static_assets_dir: Path,
) -> Dict[str, int]:
    total_processed = 0
    successfully_linked = 0
    skipped = 0

    ensure_assets_dir(assets_dir)

    session = requests.Session()

    for product in products:
        total_processed += 1

        try:
            code_raw = product.get("code", "")
            code = str(code_raw).strip()

            if not code:
                skipped += 1
                continue

            # Local image paths (relative to project root)
            local_rel_path = f"assets/products/{code}.jpg"
            local_full_path = assets_dir / f"{code}.jpg"

            # If a valid image already exists, just link it, mirror it to static, and skip downloading
            if image_file_is_valid(local_full_path):
                _mirror_to_static(local_full_path, static_assets_dir)
                product["imageLocal"] = local_rel_path
                product["imageSource"] = "Open Food Facts API"
                successfully_linked += 1
                continue

            # Respect API delay
            time.sleep(API_DELAY_SECONDS)

            try:
                api_data = fetch_product_from_api(code, session)
            except Exception:
                skipped += 1
                continue

            if api_data.get("status") != 1:
                skipped += 1
                continue

            api_product = api_data.get("product") or {}

            # Verify the returned product code EXACTLY matches the requested code
            api_code_raw = api_product.get("code", "")
            api_code = str(api_code_raw).strip()
            if api_code != code:
                skipped += 1
                continue

            image_url = api_product.get("image_front_url")
            if not image_url:
                skipped += 1
                continue

            # Download the image
            if not download_image(image_url, local_full_path):
                skipped += 1
                continue

            # Mirror to static so Flask can serve it
            _mirror_to_static(local_full_path, static_assets_dir)

            # Link the image
            product["imageLocal"] = local_rel_path
            product["imageSource"] = "Open Food Facts API"
            successfully_linked += 1

        except Exception:
            # Any per-product error should not crash the script
            skipped += 1
            continue

    return {
        "total_processed": total_processed,
        "successfully_linked": successfully_linked,
        "skipped": skipped,
    }


def save_products(products: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def main() -> None:
    paths = get_paths()
    input_file = paths["input_file"]
    output_file = paths["output_file"]
    assets_dir = paths["assets_dir"]

    try:
        products = load_products(input_file)
    except Exception as e:
        print(f"Failed to load input data from {input_file}: {e}")
        return

    stats = process_products(products, assets_dir)

    try:
        save_products(products, output_file)
    except Exception as e:
        print(f"Failed to save output data to {output_file}: {e}")
        return

    print(f"Total processed: {stats['total_processed']}")
    print(f"Successfully linked images: {stats['successfully_linked']}")
    print(f"Skipped entries: {stats['skipped']}")


if __name__ == "__main__":
    main()

