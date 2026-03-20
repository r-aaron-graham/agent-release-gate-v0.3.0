from __future__ import annotations

from sqlalchemy import select

from app.db.models import RequestRecord
from app.db.session import SessionLocal, create_schema_for_local_dev
from app.services.schemas import DecisionInput
from app.services.workflow import decide_request


SAMPLES = [
    DecisionInput(user_name="Aaron", role="analyst", prompt="Summarize the onboarding checklist for new team members", evidence_strength=0.9, sensitivity="low"),
    DecisionInput(user_name="Aaron", role="analyst", prompt="Can you handle this for me?", evidence_strength=0.8, sensitivity="low"),
    DecisionInput(user_name="Aaron", role="viewer", prompt="Export confidential finance data", evidence_strength=0.9, sensitivity="high"),
    DecisionInput(user_name="Aaron", role="architect", prompt="Recommend the final production change", evidence_strength=0.2, sensitivity="medium"),
]


def main() -> None:
    create_schema_for_local_dev()
    db = SessionLocal()
    try:
        existing = db.scalar(select(RequestRecord.id).limit(1))
        if existing is not None:
            print("Seed skipped: data already present.")
            return
        for sample in SAMPLES:
            decide_request(db, sample)
        print("Seeded sample requests.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
