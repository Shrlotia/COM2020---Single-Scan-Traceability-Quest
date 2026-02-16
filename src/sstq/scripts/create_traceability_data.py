"""Generate random Stage/Breakdown/Claim/Evidence data for existing products.

Usage examples:
  python sstq.scripts.create_traceability_data 
  (default: generates all data types for all products)
  python sstq.scripts.create_traceability_data --barcode 0009542005979 --only timeline claims 
  (generates only timeline and claims for the specified product)
  python sstq.scripts.create_traceability_data --replace-existing --seed 42 
  (defaults to all data types for all products, but with deterministic random values and overwriting existing data)
"""

from __future__ import annotations

import argparse
import random
from datetime import date, datetime, time, timedelta
from typing import Iterable

from sstq import create_app
from sstq.extensions import db
from sstq.models import Breakdown, Claim, Evidence, Product, Stage

COUNTRIES = [
    "United Kingdom",
    "France",
    "Germany",
    "Spain",
    "Italy",
    "Brazil",
    "Peru",
    "India",
    "Vietnam",
    "Thailand",
    "Kenya",
    "United States",
    "Canada",
]

REGIONS = [
    "North",
    "South",
    "East",
    "West",
    "Central",
    "Coastal",
    "Highland",
    "River Basin",
]

STAGE_TYPES = [
    "Raw Material Sourcing",
    "Primary Processing",
    "Quality Check",
    "Packaging",
    "Distribution",
    "Retail Delivery",
]

BREAKDOWN_NAMES = [
    "Primary Ingredient",
    "Secondary Ingredient",
    "Packaging Material",
    "Assembly",
    "Finishing",
]

CLAIM_TYPES = [
    "Origin",
    "Sustainability",
    "Ethical Sourcing",
    "Quality",
    "Certification",
]

CLAIM_TEMPLATES = [
    "Core ingredients are sourced from verified suppliers.",
    "Production follows documented quality controls.",
    "Supply chain records are available for review.",
    "Traceability information has been updated this quarter.",
    "Sourcing aligns with published procurement standards.",
]

CONFIDENCE_LABELS = ["verified", "partially-verified", "unverified"]

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


def _random_choice(items: list[str]) -> str:
    return random.choice(items)


def _build_stage_window(base_start: date) -> tuple[date, date]:
    start = base_start + timedelta(days=random.randint(2, 20))
    end = start + timedelta(days=random.randint(2, 14))
    return start, end


def _random_weights(count: int) -> list[float]:
    raw = [random.random() for _ in range(count)]
    total = sum(raw)
    if total == 0:
        return [100.0 / count] * count

    values = [round((value / total) * 100, 2) for value in raw]
    drift = round(100 - sum(values), 2)
    values[-1] = round(values[-1] + drift, 2)
    return values


def _pick_products(barcode: str | None, limit: int | None) -> list[Product]:
    if barcode:
        product = db.session.get(Product, barcode)
        return [product] if product else []

    query = Product.query.order_by(Product.name.asc())
    if limit:
        query = query.limit(limit)
    return query.all()


def create_timeline(
    products: Iterable[Product],
    stages_per_product: int = 4,
    replace_existing: bool = False,
) -> int:
    """Create random Stage rows for each given product."""
    created = 0
    today = date.today()

    for product in products:
        if replace_existing:
            Stage.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)
        elif product.stages:
            continue

        start_cursor = today - timedelta(days=random.randint(180, 360))
        for _ in range(max(1, stages_per_product)):
            stage_start, stage_end = _build_stage_window(start_cursor)
            start_cursor = stage_end
            db.session.add(
                Stage(
                    product_barcode=product.barcode,
                    stage_type=_random_choice(STAGE_TYPES),
                    country=_random_choice(COUNTRIES),
                    region=_random_choice(REGIONS),
                    start_date=stage_start,
                    end_date=stage_end,
                    description=f"{product.name} moved through {_random_choice(STAGE_TYPES).lower()} in this period.",
                )
            )
            created += 1

    return created


def create_breakdown(
    products: Iterable[Product],
    breakdowns_per_product: int = 3,
    replace_existing: bool = False,
) -> int:
    """Create random Breakdown rows for each given product."""
    created = 0

    for product in products:
        if replace_existing:
            Breakdown.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)
        elif product.breakdowns:
            continue

        count = max(1, breakdowns_per_product)
        percentages = _random_weights(count)
        for index in range(count):
            db.session.add(
                Breakdown(
                    product_barcode=product.barcode,
                    breakdown_name=BREAKDOWN_NAMES[index % len(BREAKDOWN_NAMES)],
                    country=_random_choice(COUNTRIES),
                    percentage=percentages[index],
                    notes=f"Estimated contribution for batch {random.randint(1000, 9999)}.",
                )
            )
            created += 1

    return created


def create_claim_cards(
    products: Iterable[Product],
    claims_per_product: int = 3,
    replace_existing: bool = False,
) -> int:
    """Create random Claim rows for each given product."""
    created = 0

    for product in products:
        if replace_existing:
            existing_claims = Claim.query.filter_by(product_barcode=product.barcode).all()
            if existing_claims:
                claim_ids = [claim.claim_id for claim in existing_claims]
                Evidence.query.filter(Evidence.claim_id.in_(claim_ids)).delete(synchronize_session=False)
                Claim.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)
        elif product.claims:
            continue

        for _ in range(max(1, claims_per_product)):
            db.session.add(
                Claim(
                    product_barcode=product.barcode,
                    claim_type=_random_choice(CLAIM_TYPES),
                    claim_text=_random_choice(CLAIM_TEMPLATES),
                    confidence_label=_random_choice(CONFIDENCE_LABELS),
                    rationale="Generated helper data for development and demo usage.",
                )
            )
            created += 1

    return created


def create_evidence(
    products: Iterable[Product],
    evidence_per_claim: int = 2,
    replace_existing: bool = False,
) -> int:
    """Create random Evidence rows for each claim under given products."""
    created = 0
    now = datetime.utcnow()

    for product in products:
        claims = list(product.claims)
        if not claims:
            continue

        for claim in claims:
            if replace_existing:
                Evidence.query.filter_by(claim_id=claim.claim_id).delete(synchronize_session=False)
            elif claim.evidence:
                continue

            for _ in range(max(1, evidence_per_claim)):
                evidence_date = now - timedelta(days=random.randint(3, 365))
                db.session.add(
                    Evidence(
                        claim_id=claim.claim_id,
                        evidence_type=_random_choice(EVIDENCE_TYPES),
                        issuer=_random_choice(ISSUERS),
                        date=datetime.combine(evidence_date.date(), time.min),
                        summary=f"Evidence generated for claim {claim.claim_id} ({claim.claim_type}).",
                        file_reference=f"docs/evidence-{claim.claim_id}-{random.randint(100, 999)}.pdf",
                    )
                )
                created += 1

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate random traceability records for existing products.")
    parser.add_argument("--barcode", help="Generate data only for this product barcode.")
    parser.add_argument("--limit", type=int, help="Limit number of products when barcode is not provided.")
    parser.add_argument("--seed", type=int, help="Random seed for deterministic output.")
    parser.add_argument("--replace-existing", action="store_true", help="Overwrite existing data for selected sections.")
    parser.add_argument("--timeline-per-product", type=int, default=4)
    parser.add_argument("--breakdown-per-product", type=int, default=3)
    parser.add_argument("--claims-per-product", type=int, default=3)
    parser.add_argument("--evidence-per-claim", type=int, default=2)
    parser.add_argument(
        "--only",
        nargs="+",
        choices=["timeline", "breakdown", "claims", "evidence"],
        help="Run only selected generators. Default runs all.",
    )
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

        selected = set(args.only or ["timeline", "breakdown", "claims", "evidence"])
        counters = {"timeline": 0, "breakdown": 0, "claims": 0, "evidence": 0}

        if "timeline" in selected:
            counters["timeline"] = create_timeline(
                products,
                stages_per_product=args.timeline_per_product,
                replace_existing=args.replace_existing,
            )

        if "breakdown" in selected:
            counters["breakdown"] = create_breakdown(
                products,
                breakdowns_per_product=args.breakdown_per_product,
                replace_existing=args.replace_existing,
            )

        if "claims" in selected:
            counters["claims"] = create_claim_cards(
                products,
                claims_per_product=args.claims_per_product,
                replace_existing=args.replace_existing,
            )

        # Refresh relationships if claims were changed before evidence generation.
        if "evidence" in selected:
            db.session.flush()
            refreshed_products = _pick_products(args.barcode, args.limit)
            counters["evidence"] = create_evidence(
                refreshed_products,
                evidence_per_claim=args.evidence_per_claim,
                replace_existing=args.replace_existing,
            )

        db.session.commit()
        print(
            "Generated:",
            f"timeline={counters['timeline']}",
            f"breakdown={counters['breakdown']}",
            f"claims={counters['claims']}",
            f"evidence={counters['evidence']}",
            f"products={len(products)}",
        )


if __name__ == "__main__":
    main()
