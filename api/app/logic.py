"""Pure-function comp logic used by both API and seeder."""
from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import date


@dataclass
class CommissionResult:
    bookings_total: float
    quota_amount: float
    attainment_pct: float
    base_commission: float
    accelerator_commission: float
    kicker_commission: float
    total_commission: float
    explanation: List[str] = field(default_factory=list)


def quarter_for_date(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}"


def quarter_bounds(period: str) -> Tuple[date, date]:
    year = int(period[:4])
    q = int(period[-1])
    start_month = (q - 1) * 3 + 1
    end_month = start_month + 2
    from calendar import monthrange
    start = date(year, start_month, 1)
    end = date(year, end_month, monthrange(year, end_month)[1])
    return start, end


def compute_commission(
    bookings_total: float,
    quota_amount: float,
    commission_rate: float,
    accelerator_100: float,
    accelerator_120: float,
    kicker_new_logo_rate: float,
    new_logo_bookings: float,
) -> CommissionResult:
    """Tiered commission model with two accelerator brackets."""
    if quota_amount <= 0:
        attainment = 0.0
    else:
        attainment = bookings_total / quota_amount

    # Bookings buckets
    bookings_under_100 = min(bookings_total, quota_amount)
    bookings_100_120 = max(0.0, min(bookings_total, quota_amount * 1.20) - quota_amount)
    bookings_over_120 = max(0.0, bookings_total - quota_amount * 1.20)

    base_c = bookings_under_100 * commission_rate
    accel_c = (
        bookings_100_120 * commission_rate * accelerator_100
        + bookings_over_120 * commission_rate * accelerator_120
    )
    kicker_c = new_logo_bookings * kicker_new_logo_rate

    total = base_c + accel_c + kicker_c

    explanation = [
        f"Bookings: ${bookings_total:,.0f} vs quota ${quota_amount:,.0f} = {attainment*100:.1f}% attainment.",
        f"Base commission: ${bookings_under_100:,.0f} x {commission_rate*100:.2f}% = ${base_c:,.2f}.",
    ]
    if bookings_100_120 > 0:
        explanation.append(
            f"Accelerator (100-120%): ${bookings_100_120:,.0f} x {commission_rate*100:.2f}% x {accelerator_100:.2f} = ${bookings_100_120 * commission_rate * accelerator_100:,.2f}."
        )
    if bookings_over_120 > 0:
        explanation.append(
            f"Accelerator (>120%): ${bookings_over_120:,.0f} x {commission_rate*100:.2f}% x {accelerator_120:.2f} = ${bookings_over_120 * commission_rate * accelerator_120:,.2f}."
        )
    if kicker_c > 0:
        explanation.append(
            f"New-logo kicker: ${new_logo_bookings:,.0f} x {kicker_new_logo_rate*100:.2f}% = ${kicker_c:,.2f}."
        )
    explanation.append(f"Total commission: ${total:,.2f}.")

    return CommissionResult(
        bookings_total=round(bookings_total, 2),
        quota_amount=round(quota_amount, 2),
        attainment_pct=round(attainment * 100, 2),
        base_commission=round(base_c, 2),
        accelerator_commission=round(accel_c, 2),
        kicker_commission=round(kicker_c, 2),
        total_commission=round(total, 2),
        explanation=explanation,
    )


def percentile(values: List[float], p: float) -> float:
    """Simple linear-interpolation percentile (p in 0..1)."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def median(values: List[float]) -> float:
    return percentile(values, 0.5)
