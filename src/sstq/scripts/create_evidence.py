"""Generate evidence rows and matching PDF files for existing claims.

Usage:
  python ./src/sstq/scripts/create_evidence.py
  python ./src/sstq/scripts/create_evidence.py --limit 20 --seed 42
  python ./src/sstq/scripts/create_evidence.py --barcode 0009542005979 --replace-existing
"""

from __future__ import annotations

import argparse
import random
import sys
import textwrap
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sstq import create_app
from sstq.extensions import db
from sstq.models import Claim, Evidence, Product

EVIDENCE_TYPES = [
    "Certificate",
    "Audit Report",
    "Invoice",
    "Shipment Record",
    "Lab Result",
    "Supplier Statement",
]

ISSUERS = [
    "Internal QA Team",
    "Third-Party Auditor",
    "Supplier Compliance Office",
    "Regional Trade Authority",
    "Independent Lab",
]

SUMMARY_TEMPLATES = [
    "Supporting record confirming the traceability claim for this product batch.",
    "Documented evidence reviewed for demo and verification workflow coverage.",
    "Evidence item generated to support product passport claim review.",
    "Attached record summarising issuer confirmation and traceability checks.",
]

VERIFICATION_CHECKS = [
    "Supplier identity matched against registered onboarding records.",
    "Batch and shipment references aligned with the claimed product lot.",
    "Supporting dates fell within the declared production period.",
    "Country and stage metadata were consistent with the product passport.",
]

REVIEW_OUTCOMES = [
    "No critical inconsistencies detected in the submitted supporting record.",
    "Evidence supports the stated claim within the scope of the sampled batch.",
    "Document package is suitable for verifier review and consumer passport drill-down.",
]

STATIC_EVIDENCE_DIR = PROJECT_ROOT / "src" / "sstq" / "static" / "uploads" / "evidence"
STATIC_EVIDENCE_URL_PREFIX = "/static/uploads/evidence"


def _clean_text(value: str) -> str:
    return "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in str(value or "")).strip()


def _escape_pdf_text(value: str) -> str:
    return (
        _clean_text(value)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _random_choice(items: list[str]) -> str:
    return random.choice(items)


def _pick_products(barcode: str | None, limit: int | None) -> list[Product]:
    if barcode:
        product = db.session.get(Product, barcode)
        return [product] if product else []

    query = Product.query.order_by(Product.name.asc())
    if limit:
        query = query.limit(limit)
    return query.all()


def _generated_file_paths(claim: Claim) -> list[Path]:
    files = []
    for evidence in claim.evidence:
        if not evidence.file_reference:
            continue
        file_reference = str(evidence.file_reference)
        if not file_reference.startswith(STATIC_EVIDENCE_URL_PREFIX):
            continue
        relative_name = file_reference.removeprefix(STATIC_EVIDENCE_URL_PREFIX).lstrip("/")
        file_path = STATIC_EVIDENCE_DIR / relative_name
        files.append(file_path)
    return files


def _pdf_bytes(lines: list[str]) -> bytes:
    text_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for index, line in enumerate(lines):
        prefix = "" if index == 0 else "T* "
        text_lines.append(f"{prefix}({_escape_pdf_text(line)}) Tj")
    text_lines.append("ET")
    stream = "\n".join(text_lines).encode("ascii", "ignore")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _wrap_line(value: str, width: int = 74) -> list[str]:
    clean = _clean_text(value)
    if not clean:
        return [""]
    return textwrap.wrap(clean, width=width) or [clean]


def _evidence_document_lines(
    *,
    product: Product,
    claim: Claim,
    evidence_type: str,
    issuer: str,
    summary: str,
    evidence_date: datetime,
    reference_code: str,
) -> list[str]:
    checks = random.sample(VERIFICATION_CHECKS, k=min(3, len(VERIFICATION_CHECKS)))
    lines = [
        "TRACEABILITY SUPPORTING EVIDENCE",
        "",
        f"Evidence Reference: {reference_code}",
        f"Document Type: {evidence_type}",
        f"Issued By: {issuer}",
        f"Issue Date: {evidence_date.date().isoformat()}",
        "Review Status: Available for verifier and consumer evidence view",
        "",
        "PRODUCT DETAILS",
        f"Product Name: {product.name}",
        f"Barcode: {product.barcode}",
        f"Brand: {product.brand}",
        f"Category: {product.category}",
        "",
        "CLAIM UNDER REVIEW",
        f"Claim Type: {claim.claim_type}",
    ]
    lines.extend(_wrap_line(f"Claim Text: {claim.claim_text}"))
    lines.extend(
        [
            f"Confidence Label: {claim.confidence_label or 'pending review'}",
            "",
            "EVIDENCE SUMMARY",
        ]
    )
    lines.extend(_wrap_line(summary))
    lines.extend(
        [
            "",
            "VERIFICATION NOTES",
        ]
    )
    for check in checks:
        lines.extend(_wrap_line(f"- {check}"))
    lines.extend(
        [
            "",
            "CHAIN OF CUSTODY SNAPSHOT",
            f"- Linked claim id: {claim.claim_id}",
            f"- Linked product barcode: {product.barcode}",
            f"- Document issuer: {issuer}",
            f"- Review timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "REVIEW OUTCOME",
        ]
    )
    lines.extend(_wrap_line(_random_choice(REVIEW_OUTCOMES)))
    lines.extend(
        [
            "",
            "SIGN-OFF",
            f"Prepared for: {product.brand} traceability passport demo",
            "Verifier Note: Generated supporting file for coursework dataset and UI walkthrough.",
        ]
    )
    return lines[:48]


def _write_pdf(file_path: Path, *, product: Product, claim: Claim, evidence_type: str, issuer: str, summary: str, evidence_date: datetime) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    reference_code = f"EV-{product.barcode}-{claim.claim_id}-{evidence_date.strftime('%Y%m%d')}"
    lines = _evidence_document_lines(
        product=product,
        claim=claim,
        evidence_type=evidence_type,
        issuer=issuer,
        summary=summary,
        evidence_date=evidence_date,
        reference_code=reference_code,
    )
    file_path.write_bytes(_pdf_bytes(lines))


def _file_reference(product: Product, claim: Claim, index: int) -> tuple[Path, str]:
    safe_barcode = _clean_text(product.barcode).replace(" ", "_")
    filename = f"{safe_barcode}-claim-{claim.claim_id}-evidence-{index}.pdf"
    return STATIC_EVIDENCE_DIR / filename, f"{STATIC_EVIDENCE_URL_PREFIX}/{filename}"


def create_evidence(
    products: Iterable[Product],
    evidence_per_claim: int = 2,
    replace_existing: bool = False,
) -> int:
    created = 0
    now = datetime.utcnow()

    for product in products:
        claims = list(product.claims)
        if not claims:
            continue

        for claim in claims:
            if replace_existing:
                for file_path in _generated_file_paths(claim):
                    file_path.unlink(missing_ok=True)
                Evidence.query.filter_by(claim_id=claim.claim_id).delete(synchronize_session=False)
                db.session.flush()
            elif claim.evidence:
                continue

            for index in range(1, max(1, evidence_per_claim) + 1):
                evidence_type = _random_choice(EVIDENCE_TYPES)
                issuer = _random_choice(ISSUERS)
                evidence_date = now - timedelta(days=random.randint(3, 365))
                summary = _random_choice(SUMMARY_TEMPLATES)
                file_path, file_reference = _file_reference(product, claim, index)

                _write_pdf(
                    file_path,
                    product=product,
                    claim=claim,
                    evidence_type=evidence_type,
                    issuer=issuer,
                    summary=summary,
                    evidence_date=evidence_date,
                )

                db.session.add(
                    Evidence(
                        claim_id=claim.claim_id,
                        evidence_type=evidence_type,
                        issuer=issuer,
                        date=datetime.combine(evidence_date.date(), time.min),
                        summary=summary,
                        file_reference=file_reference,
                    )
                )
                created += 1

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate evidence rows and PDF files for existing product claims.")
    parser.add_argument("--barcode", help="Generate evidence only for this product barcode.")
    parser.add_argument("--limit", type=int, help="Limit number of products when barcode is not provided.")
    parser.add_argument("--seed", type=int, help="Random seed for deterministic output.")
    parser.add_argument("--replace-existing", action="store_true", help="Overwrite existing evidence for selected products.")
    parser.add_argument("--evidence-per-claim", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    app = create_app()
    with app.app_context():
        products = _pick_products(args.barcode, args.limit)
        if not products:
            print("No matching products found. Nothing generated.")
            return

        created = create_evidence(
            products,
            evidence_per_claim=args.evidence_per_claim,
            replace_existing=args.replace_existing,
        )
        db.session.commit()
        print(
            "Generated:",
            f"evidence={created}",
            f"products={len(products)}",
            f"output_dir={STATIC_EVIDENCE_DIR}",
        )


if __name__ == "__main__":
    main()
