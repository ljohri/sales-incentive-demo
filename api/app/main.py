from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from .db import get_db, engine, Base
from . import models, schemas
from .logic import compute_commission, median, percentile

app = FastAPI(
    title="ICM Demo API",
    description=(
        "A toy Incentive Compensation Management backend used for demoing "
        "Claude as an agentic co-worker over real sales-incentive APIs."
    ),
    version="1.0.0",
)

Base.metadata.create_all(engine)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


def _resolve_rep(db: Session, rep: str) -> models.Rep:
    """Look up a rep by employee_id, email, or 'First Last' / first name."""
    q = db.query(models.Rep)
    # exact employee_id
    r = q.filter(models.Rep.employee_id.ilike(rep)).first()
    if r:
        return r
    # exact email
    r = q.filter(models.Rep.email.ilike(rep)).first()
    if r:
        return r
    # "First Last"
    parts = rep.strip().split()
    if len(parts) >= 2:
        r = q.filter(
            and_(
                models.Rep.first_name.ilike(parts[0]),
                models.Rep.last_name.ilike(parts[-1]),
            )
        ).first()
        if r:
            return r
    # first name unique?
    matches = q.filter(models.Rep.first_name.ilike(rep)).all()
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(f"{m.first_name} {m.last_name}" for m in matches)
        raise HTTPException(
            status_code=409,
            detail=f"Ambiguous rep '{rep}'. Matches: {names}. Use employee_id or full name.",
        )
    raise HTTPException(status_code=404, detail=f"No rep found for '{rep}'.")


# ---------- Reps ----------

@app.get("/reps", response_model=List[schemas.RepOut])
def list_reps(
    role: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Rep)
    if role:
        q = q.filter(models.Rep.role.ilike(role))
    if region:
        q = q.filter(models.Rep.region.ilike(region))
    return q.order_by(models.Rep.last_name).all()


@app.get("/reps/{rep}", response_model=schemas.RepOut)
def get_rep(rep: str, db: Session = Depends(get_db)):
    return _resolve_rep(db, rep)


# ---------- Incentive Plans ----------

@app.get("/incentive-plans", response_model=List[schemas.IncentivePlanOut])
def list_plans(
    role: Optional[str] = None,
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.IncentivePlan)
    if role:
        q = q.filter(models.IncentivePlan.role.ilike(role))
    if as_of:
        q = q.filter(
            and_(
                models.IncentivePlan.effective_start <= as_of,
                or_(
                    models.IncentivePlan.effective_end == None,  # noqa: E711
                    models.IncentivePlan.effective_end >= as_of,
                ),
            )
        )
    return q.order_by(models.IncentivePlan.role, models.IncentivePlan.effective_start).all()


@app.get("/incentive-plans/for-rep/{rep}", response_model=schemas.IncentivePlanOut)
def plan_for_rep(rep: str, as_of: Optional[date] = None, db: Session = Depends(get_db)):
    r = _resolve_rep(db, rep)
    target = as_of or date.today()
    plan = (
        db.query(models.IncentivePlan)
        .filter(models.IncentivePlan.role == r.role)
        .filter(models.IncentivePlan.effective_start <= target)
        .filter(
            or_(
                models.IncentivePlan.effective_end == None,  # noqa: E711
                models.IncentivePlan.effective_end >= target,
            )
        )
        .order_by(models.IncentivePlan.effective_start.desc())
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found for that rep / date.")
    return plan


# ---------- Quota Attainment ----------

@app.get("/quota-attainment", response_model=schemas.QuotaAttainment)
def get_quota_attainment(
    rep: str = Query(..., description="employee_id, email, or 'First Last'"),
    period: str = Query(..., description="e.g. 2024Q2"),
    db: Session = Depends(get_db),
):
    r = _resolve_rep(db, rep)
    quota = (
        db.query(models.Quota)
        .filter(models.Quota.rep_id == r.id, models.Quota.period == period)
        .first()
    )
    if not quota:
        raise HTTPException(
            status_code=404,
            detail=f"No quota set for {r.first_name} {r.last_name} in {period}.",
        )
    rows = (
        db.query(
            func.coalesce(func.sum(models.Booking.amount), 0.0),
            func.count(models.Booking.id),
        )
        .filter(models.Booking.rep_id == r.id, models.Booking.period == period)
        .one()
    )
    bookings_total = float(rows[0])
    deals = int(rows[1])
    attainment = (bookings_total / quota.quota_amount * 100) if quota.quota_amount else 0.0

    return schemas.QuotaAttainment(
        rep_id=r.id,
        employee_id=r.employee_id,
        name=f"{r.first_name} {r.last_name}",
        role=r.role,
        region=r.region,
        period=period,
        quota=round(quota.quota_amount, 2),
        bookings=round(bookings_total, 2),
        attainment_pct=round(attainment, 2),
        deals=deals,
    )


# ---------- Commission ----------

@app.get("/commission", response_model=schemas.CommissionBreakdown)
def calculate_commission(
    rep: str = Query(...),
    period: str = Query(...),
    recompute: bool = Query(False, description="If true, recompute from bookings rather than using stored row."),
    db: Session = Depends(get_db),
):
    r = _resolve_rep(db, rep)

    quota = (
        db.query(models.Quota)
        .filter(models.Quota.rep_id == r.id, models.Quota.period == period)
        .first()
    )
    if not quota:
        raise HTTPException(404, f"No quota for {r.first_name} {r.last_name} in {period}.")

    # Resolve plan effective during that period
    from .logic import quarter_for_date
    year = int(period[:4])
    q = int(period[-1])
    period_start = date(year, (q - 1) * 3 + 1, 1)
    plan = (
        db.query(models.IncentivePlan)
        .filter(models.IncentivePlan.role == r.role)
        .filter(models.IncentivePlan.effective_start <= period_start)
        .filter(
            or_(
                models.IncentivePlan.effective_end == None,  # noqa: E711
                models.IncentivePlan.effective_end >= period_start,
            )
        )
        .order_by(models.IncentivePlan.effective_start.desc())
        .first()
    )
    if not plan:
        raise HTTPException(404, "No active plan found for that rep / period.")

    if not recompute:
        stored = (
            db.query(models.Commission)
            .filter(models.Commission.rep_id == r.id, models.Commission.period == period)
            .first()
        )
        if stored:
            # Back out new-logo bookings from the stored kicker so the
            # explanation faithfully matches the stored totals.
            new_logo_bookings = (
                stored.kicker_commission / plan.kicker_new_logo
                if plan.kicker_new_logo > 0 else 0.0
            )
            return schemas.CommissionBreakdown(
                rep_id=r.id,
                employee_id=r.employee_id,
                name=f"{r.first_name} {r.last_name}",
                role=r.role,
                period=period,
                plan_name=plan.plan_name,
                bookings_total=stored.bookings_total,
                quota_amount=stored.quota_amount,
                attainment_pct=stored.attainment_pct,
                base_commission=stored.base_commission,
                accelerator_commission=stored.accelerator_commission,
                kicker_commission=stored.kicker_commission,
                total_commission=stored.total_commission,
                explanation=compute_commission(
                    bookings_total=stored.bookings_total,
                    quota_amount=stored.quota_amount,
                    commission_rate=plan.commission_rate,
                    accelerator_100=plan.accelerator_100,
                    accelerator_120=plan.accelerator_120,
                    kicker_new_logo_rate=plan.kicker_new_logo,
                    new_logo_bookings=new_logo_bookings,
                ).explanation,
            )

    # Recompute path
    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.rep_id == r.id, models.Booking.period == period)
        .all()
    )
    bookings_total = sum(b.amount for b in bookings)
    new_logo_total = sum(b.amount for b in bookings if b.is_new_logo)

    result = compute_commission(
        bookings_total=bookings_total,
        quota_amount=quota.quota_amount,
        commission_rate=plan.commission_rate,
        accelerator_100=plan.accelerator_100,
        accelerator_120=plan.accelerator_120,
        kicker_new_logo_rate=plan.kicker_new_logo,
        new_logo_bookings=new_logo_total,
    )

    return schemas.CommissionBreakdown(
        rep_id=r.id,
        employee_id=r.employee_id,
        name=f"{r.first_name} {r.last_name}",
        role=r.role,
        period=period,
        plan_name=plan.plan_name,
        bookings_total=result.bookings_total,
        quota_amount=result.quota_amount,
        attainment_pct=result.attainment_pct,
        base_commission=result.base_commission,
        accelerator_commission=result.accelerator_commission,
        kicker_commission=result.kicker_commission,
        total_commission=result.total_commission,
        explanation=result.explanation,
    )


# ---------- Disputes ----------

@app.post("/disputes", response_model=schemas.DisputeOut, status_code=201)
def flag_dispute(payload: schemas.DisputeIn, db: Session = Depends(get_db)):
    r = _resolve_rep(db, payload.rep_employee_id)
    if payload.category not in ("quota", "crediting", "accelerator", "other"):
        raise HTTPException(400, "category must be one of: quota, crediting, accelerator, other.")
    count = db.query(models.Dispute).count() + 1
    ticket = f"DISP-{count:05d}"
    d = models.Dispute(
        ticket_id=ticket,
        rep_id=r.id,
        period=payload.period,
        category=payload.category,
        summary=payload.summary,
        details=payload.details,
        amount_in_dispute=payload.amount_in_dispute,
        status="open",
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@app.get("/disputes", response_model=List[schemas.DisputeOut])
def list_disputes(
    rep: Optional[str] = None,
    period: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Dispute)
    if rep:
        r = _resolve_rep(db, rep)
        q = q.filter(models.Dispute.rep_id == r.id)
    if period:
        q = q.filter(models.Dispute.period == period)
    if status:
        q = q.filter(models.Dispute.status == status)
    return q.order_by(models.Dispute.opened_at.desc()).all()


# ---------- Team Benchmarks ----------

@app.get("/team-benchmark", response_model=schemas.TeamBenchmark)
def get_team_benchmark(
    period: str = Query(..., description="e.g. 2024Q2"),
    role: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(models.Commission, models.Rep)
        .join(models.Rep, models.Rep.id == models.Commission.rep_id)
        .filter(models.Commission.period == period)
    )
    if role:
        q = q.filter(models.Rep.role.ilike(role))
    if region:
        q = q.filter(models.Rep.region.ilike(region))
    rows = q.all()
    if not rows:
        raise HTTPException(404, "No commission rows for that filter.")

    attainments = [c.attainment_pct for c, _ in rows]
    quota_total = sum(c.quota_amount for c, _ in rows)
    bookings_total = sum(c.bookings_total for c, _ in rows)

    rows_sorted = sorted(rows, key=lambda x: x[0].attainment_pct, reverse=True)
    top = rows_sorted[0][1]
    bottom = rows_sorted[-1][1]

    return schemas.TeamBenchmark(
        period=period,
        role=role,
        region=region,
        rep_count=len(rows),
        quota_total=round(quota_total, 2),
        bookings_total=round(bookings_total, 2),
        attainment_median_pct=round(median(attainments), 2),
        attainment_top_decile_pct=round(percentile(attainments, 0.9), 2),
        attainment_mean_pct=round(sum(attainments) / len(attainments), 2),
        top_performer=f"{top.first_name} {top.last_name} ({top.employee_id})",
        bottom_performer=f"{bottom.first_name} {bottom.last_name} ({bottom.employee_id})",
    )


# ---------- Bookings (helpful for the agent to "show its work") ----------

@app.get("/bookings")
def list_bookings(
    rep: str = Query(...),
    period: Optional[str] = None,
    db: Session = Depends(get_db),
):
    r = _resolve_rep(db, rep)
    q = db.query(models.Booking).filter(models.Booking.rep_id == r.id)
    if period:
        q = q.filter(models.Booking.period == period)
    rows = q.order_by(models.Booking.booked_date.desc()).all()
    return [
        {
            "deal_id": b.deal_id,
            "account": b.account,
            "booked_date": b.booked_date.isoformat(),
            "amount": b.amount,
            "period": b.period,
            "is_new_logo": b.is_new_logo,
        }
        for b in rows
    ]
