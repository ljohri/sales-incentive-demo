"""Seed the database with a realistic 5-year sales org.

Idempotent: if reps already exist, exits without changes unless RESEED=true.
"""
import os
import random
from datetime import date, timedelta, datetime
from typing import List

from sqlalchemy import inspect

from .db import engine, SessionLocal, Base
from . import models
from .logic import compute_commission, quarter_for_date


REGIONS = {
    "West": ["NorCal", "SoCal", "Pacific NW", "Mountain West"],
    "Central": ["Texas", "Great Lakes", "Plains", "Heartland"],
    "East": ["Northeast", "Mid-Atlantic", "Florida", "New England"],
    "South": ["Southeast", "Gulf", "Carolinas", "Appalachia"],
}

FIRST_NAMES = [
    "Jordan", "Alex", "Priya", "Marcus", "Sofia", "Kai", "Riley", "Noah",
    "Emma", "Liam", "Ava", "Diego", "Mei", "Omar", "Hana", "Ethan",
    "Zara", "Leo", "Maya", "Cole", "Ivy", "Theo", "Nina", "Sam"
]
LAST_NAMES = [
    "Patel", "Nguyen", "Garcia", "Smith", "Johnson", "Kim", "Williams",
    "Brown", "Davis", "Martinez", "Lopez", "Wilson", "Anderson", "Taylor",
    "Thomas", "Moore", "Jackson", "White", "Harris", "Clark", "Lewis",
    "Walker", "Hall", "Young"
]

ACCOUNT_NAMES = [
    "Acme Corp", "Northwind", "Globex", "Initech", "Umbrella", "Hooli",
    "Stark Industries", "Wonka", "Wayne Enterprises", "Cyberdyne",
    "Tyrell", "Aperture", "Soylent", "Massive Dynamic", "Pied Piper",
    "Vandelay", "Dunder Mifflin", "Bluth Co", "Sterling Cooper", "Krusty Krab",
    "Aviato", "Oscorp", "Gringotts", "Weyland-Yutani", "InGen",
    "Monsters Inc", "Compuglobalhypermeganet", "Prestige Worldwide", "Vehement Capital",
    "Buy n Large", "Cogswell Cogs", "Spacely Sprockets",
]


def quarters_between(start: date, end: date) -> List[str]:
    out = []
    y, q = start.year, (start.month - 1) // 3 + 1
    ey, eq = end.year, (end.month - 1) // 3 + 1
    while (y, q) <= (ey, eq):
        out.append(f"{y}Q{q}")
        q += 1
        if q == 5:
            q = 1
            y += 1
    return out


def _quarter_start(period: str) -> date:
    year = int(period[:4])
    q = int(period[-1])
    return date(year, (q - 1) * 3 + 1, 1)


def build_plans(db) -> dict:
    """Two plan generations: pre-2024 and 2024+. Returns role -> list of plans (in order)."""
    plans = []
    plans.append(models.IncentivePlan(
        role="SDR", plan_name="SDR Plan 2021",
        effective_start=date(2021, 1, 1), effective_end=date(2023, 12, 31),
        base_salary=55_000, on_target_variable=35_000,
        commission_rate=0.05, accelerator_100=1.0, accelerator_120=1.0,
        kicker_new_logo=0.01,
        notes="Pre-2024 SDR plan: flat 5% with small new-logo kicker.",
    ))
    plans.append(models.IncentivePlan(
        role="SDR", plan_name="SDR Plan 2024",
        effective_start=date(2024, 1, 1), effective_end=None,
        base_salary=60_000, on_target_variable=40_000,
        commission_rate=0.06, accelerator_100=1.25, accelerator_120=1.5,
        kicker_new_logo=0.015,
        notes="Refreshed SDR plan with mild accelerators to reward overperformance.",
    ))
    plans.append(models.IncentivePlan(
        role="AE", plan_name="AE Plan 2021",
        effective_start=date(2021, 1, 1), effective_end=date(2023, 12, 31),
        base_salary=110_000, on_target_variable=110_000,
        commission_rate=0.08, accelerator_100=1.5, accelerator_120=2.0,
        kicker_new_logo=0.02,
        notes="Classic AE plan: 8% base, 1.5x then 2x accelerators.",
    ))
    plans.append(models.IncentivePlan(
        role="AE", plan_name="AE Plan 2024",
        effective_start=date(2024, 1, 1), effective_end=None,
        base_salary=120_000, on_target_variable=120_000,
        commission_rate=0.09, accelerator_100=1.5, accelerator_120=2.0,
        kicker_new_logo=0.025,
        notes="AE plan refresh with higher base rate and richer new-logo kicker.",
    ))
    plans.append(models.IncentivePlan(
        role="EAE", plan_name="Enterprise AE Plan 2021",
        effective_start=date(2021, 1, 1), effective_end=date(2023, 12, 31),
        base_salary=150_000, on_target_variable=150_000,
        commission_rate=0.10, accelerator_100=1.75, accelerator_120=2.25,
        kicker_new_logo=0.025,
        notes="Enterprise AE: bigger deals, steeper accelerators.",
    ))
    plans.append(models.IncentivePlan(
        role="EAE", plan_name="Enterprise AE Plan 2024",
        effective_start=date(2024, 1, 1), effective_end=None,
        base_salary=160_000, on_target_variable=160_000,
        commission_rate=0.10, accelerator_100=1.75, accelerator_120=2.5,
        kicker_new_logo=0.03,
        notes="Enterprise AE plan refresh — top-end accelerator bumped to 2.5x.",
    ))

    for p in plans:
        db.add(p)
    db.flush()

    role_plans: dict = {}
    for p in plans:
        role_plans.setdefault(p.role, []).append(p)
    for v in role_plans.values():
        v.sort(key=lambda x: x.effective_start)
    return role_plans


def pick_plan(role_plans: dict, role: str, period: str) -> models.IncentivePlan:
    start = _quarter_start(period)
    for p in role_plans[role]:
        if p.effective_start <= start and (p.effective_end is None or p.effective_end >= start):
            return p
    return role_plans[role][-1]


def role_quota_for_period(role: str, period: str) -> float:
    """Quarterly quota by role, with mild year-over-year growth."""
    year = int(period[:4])
    growth = 1.0 + 0.05 * (year - 2021)  # 5% YoY
    base = {"SDR": 250_000, "AE": 900_000, "EAE": 1_800_000}[role]
    return round(base * growth, -3)


def build_reps(db) -> List[models.Rep]:
    random.seed(int(os.environ.get("RANDOM_SEED", "42")))

    # 20 reps with a deliberate role/region distribution
    role_dist = ["SDR"] * 6 + ["AE"] * 10 + ["EAE"] * 4
    random.shuffle(role_dist)

    used_names = set()
    reps: List[models.Rep] = []
    for i in range(20):
        role = role_dist[i]
        region = random.choice(list(REGIONS.keys()))
        territory = random.choice(REGIONS[region])
        while True:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            if (fn, ln) not in used_names:
                used_names.add((fn, ln))
                break
        hire_year = random.choice([2019, 2020, 2020, 2021, 2021, 2022, 2022, 2023])
        hire_month = random.randint(1, 12)
        hire = date(hire_year, hire_month, random.randint(1, 28))
        rep = models.Rep(
            employee_id=f"E{1000 + i:04d}",
            first_name=fn,
            last_name=ln,
            email=f"{fn.lower()}.{ln.lower()}@example.com",
            role=role,
            region=region,
            territory=territory,
            hire_date=hire,
            active=True,
        )
        db.add(rep)
        reps.append(rep)
    db.flush()
    return reps


def simulate_history(db, reps: List[models.Rep], role_plans: dict):
    """Generate quotas, bookings, commissions, and a handful of disputes."""
    rng = random.Random(int(os.environ.get("RANDOM_SEED", "42")))

    start = date(2021, 1, 1)
    end = date(2025, 12, 31)
    all_quarters = quarters_between(start, end)

    # Per-rep persistent "skill" multiplier so some reps consistently over/under perform
    rep_skill = {r.id: rng.gauss(1.0, 0.18) for r in reps}

    deal_counter = 0
    dispute_counter = 0

    for period in all_quarters:
        q_start = _quarter_start(period)
        q_year, q_q = q_start.year, (q_start.month - 1) // 3 + 1
        q_end_month = (q_q - 1) * 3 + 3
        from calendar import monthrange
        q_end = date(q_year, q_end_month, monthrange(q_year, q_end_month)[1])

        for rep in reps:
            if rep.hire_date > q_end:
                continue  # rep hadn't started yet

            quota_amount = role_quota_for_period(rep.role, period)

            # Regional uplift: West/East a bit higher quota
            if rep.region in ("West", "East"):
                quota_amount = round(quota_amount * 1.05, -3)

            db.add(models.Quota(
                rep_id=rep.id,
                period=period,
                period_year=q_year,
                period_quarter=q_q,
                quota_amount=quota_amount,
            ))

            # Generate bookings: target attainment ~ skill * noise * macro
            macro = {2021: 1.05, 2022: 1.10, 2023: 0.92, 2024: 1.00, 2025: 1.07}[q_year]
            target_attainment = rep_skill[rep.id] * rng.gauss(1.0, 0.18) * macro
            target_attainment = max(0.2, min(2.0, target_attainment))
            target_bookings = quota_amount * target_attainment

            # Split into 2-8 deals
            num_deals = max(1, int(rng.gauss(4, 1.5)))
            num_deals = max(1, min(num_deals, 10 if rep.role != "SDR" else 6))
            # SDRs book smaller deals
            deal_sizes = [max(0.02, rng.gauss(1.0, 0.4)) for _ in range(num_deals)]
            s = sum(deal_sizes)
            deal_sizes = [d / s for d in deal_sizes]

            bookings_total = 0.0
            new_logo_total = 0.0
            for ds in deal_sizes:
                deal_counter += 1
                amount = round(target_bookings * ds, 2)
                if amount <= 0:
                    continue
                # Random day within the quarter
                day_offset = rng.randint(0, (q_end - q_start).days)
                booked = q_start + timedelta(days=day_offset)
                is_new_logo = rng.random() < (0.45 if rep.role == "SDR" else 0.30)
                db.add(models.Booking(
                    rep_id=rep.id,
                    deal_id=f"D{deal_counter:07d}",
                    account=rng.choice(ACCOUNT_NAMES),
                    booked_date=booked,
                    amount=amount,
                    period=period,
                    is_new_logo=is_new_logo,
                ))
                bookings_total += amount
                if is_new_logo:
                    new_logo_total += amount

            # Compute and store commission
            plan = pick_plan(role_plans, rep.role, period)
            result = compute_commission(
                bookings_total=bookings_total,
                quota_amount=quota_amount,
                commission_rate=plan.commission_rate,
                accelerator_100=plan.accelerator_100,
                accelerator_120=plan.accelerator_120,
                kicker_new_logo_rate=plan.kicker_new_logo,
                new_logo_bookings=new_logo_total,
            )
            db.add(models.Commission(
                rep_id=rep.id,
                period=period,
                bookings_total=result.bookings_total,
                quota_amount=result.quota_amount,
                attainment_pct=result.attainment_pct,
                base_commission=result.base_commission,
                accelerator_commission=result.accelerator_commission,
                kicker_commission=result.kicker_commission,
                total_commission=result.total_commission,
                plan_id=plan.id,
            ))

            # Occasional disputes — ~3% chance per rep-quarter; bias toward under-attainment
            dispute_prob = 0.03 + (0.04 if result.attainment_pct < 70 else 0.0)
            if rng.random() < dispute_prob:
                dispute_counter += 1
                category = rng.choice(["quota", "crediting", "accelerator", "other"])
                summary_map = {
                    "quota": "Quota was set too high vs. territory potential",
                    "crediting": "Deal credit assigned to wrong rep",
                    "accelerator": "Accelerator tier not applied correctly",
                    "other": "Plan interpretation issue",
                }
                status = rng.choice(["resolved", "resolved", "rejected", "in_review", "open"])
                opened = q_end + timedelta(days=rng.randint(5, 40))
                resolved = None
                resolution_notes = None
                if status in ("resolved", "rejected"):
                    resolved = opened + timedelta(days=rng.randint(7, 30))
                    resolution_notes = (
                        "Comp ops reviewed and adjusted." if status == "resolved"
                        else "Reviewed; policy applied correctly, no change."
                    )
                db.add(models.Dispute(
                    ticket_id=f"DISP-{dispute_counter:05d}",
                    rep_id=rep.id,
                    period=period,
                    category=category,
                    summary=summary_map[category],
                    details=f"Auto-generated demo dispute for {rep.first_name} {rep.last_name} in {period}.",
                    amount_in_dispute=round(rng.uniform(500, 12000), 2),
                    status=status,
                    opened_at=datetime.combine(opened, datetime.min.time()),
                    resolved_at=datetime.combine(resolved, datetime.min.time()) if resolved else None,
                    resolution_notes=resolution_notes,
                ))


def main():
    Base.metadata.create_all(engine)

    reseed = os.environ.get("RESEED", "false").lower() == "true"
    db = SessionLocal()
    try:
        existing = db.query(models.Rep).count()
        if existing > 0 and not reseed:
            print(f"[seed] Skipping: {existing} reps already exist. Set RESEED=true to wipe.")
            return
        if reseed and existing > 0:
            print("[seed] RESEED=true — dropping & recreating schema...")
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)

        print("[seed] Building incentive plans...")
        role_plans = build_plans(db)
        print(f"[seed] Building reps...")
        reps = build_reps(db)
        print(f"[seed] Simulating 5 years of history across {len(reps)} reps...")
        simulate_history(db, reps, role_plans)
        db.commit()
        print("[seed] Done.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
