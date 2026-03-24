"""Seed demo issue reports for the verifier workflow.

Usage:
  python ./src/sstq/scripts/create_issues.py
"""

from sstq import create_app
from sstq.extensions import db
from sstq.models import Claim, Issue

TARGET_ISSUE_COUNT = 30

ISSUE_TYPES = [
    "Evidence Missing",
    "Claim Seems False",
    "Confidence Label Unclear",
    "Timeline Gap",
    "Origin Breakdown Mismatch",
]

STATUS_CYCLE = [
    ("open", None),
    ("in_review", None),
    ("resolved", "Reviewed by verifier and supporting evidence added."),
]


def main() -> None:
    app = create_app()

    with app.app_context():
        current_count = Issue.query.count()
        if current_count >= TARGET_ISSUE_COUNT:
            print(f"Issues already seeded: {current_count}")
            return

        missing_count = TARGET_ISSUE_COUNT - current_count
        claim_rows = Claim.query.order_by(Claim.claim_id.asc()).limit(missing_count).all()
        if len(claim_rows) < missing_count:
            raise RuntimeError("Not enough claims exist to seed the required number of issue reports.")

        for index, claim in enumerate(claim_rows, start=current_count):
            status, resolution_note = STATUS_CYCLE[index % len(STATUS_CYCLE)]
            issue_type = ISSUE_TYPES[index % len(ISSUE_TYPES)]
            db.session.add(
                Issue(
                    claim_id=claim.claim_id,
                    user_id=None,
                    issue_type=issue_type,
                    description=f"Seeded demo issue #{index + 1}: {issue_type.lower()} requires verifier review.",
                    status=status,
                    resolution_note=resolution_note,
                )
            )

        db.session.commit()
        print(f"Seeded issues: {Issue.query.count()}")


if __name__ == "__main__":
    main()
