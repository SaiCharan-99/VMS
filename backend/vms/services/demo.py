"""Dev-only demo data for `python -m vms.cli seed-demo`. Idempotent."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.db.models import Role, Station, Warehouse
from vms.services import users

# Fixed, well-known passwords: never run this against a real deployment.
DEMO_USERS = [
    ("operator@vms.local", "Demo Operator", Role.operator, "operator-demo-1"),
    ("reviewer@vms.local", "Demo Reviewer", Role.reviewer, "reviewer-demo-1"),
    ("admin@vms.local", "Demo Admin", Role.admin, "admin-demo-1"),
]


def seed_demo(session: Session) -> int:
    """1 warehouse, 2 stations, 1 user per role. Returns how many users were created."""
    wh = session.scalar(select(Warehouse).where(Warehouse.code == "DEMO"))
    if wh is None:
        wh = Warehouse(code="DEMO", name="Demo Warehouse")
        session.add(wh)
        session.flush()
    for code in ("ST-1", "ST-2"):
        exists = select(Station).where(Station.warehouse_id == wh.id, Station.code == code)
        if session.scalar(exists) is None:
            session.add(Station(warehouse_id=wh.id, code=code, name=f"Station {code[-1]}"))
    created = 0
    for email, name, role, password in DEMO_USERS:
        if users.get_by_email(session, email) is None:
            users.create(
                session, email=email, name=name, password=password, role=role, warehouse_id=wh.id
            )
            created += 1
    return created
