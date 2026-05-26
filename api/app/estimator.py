"""Monthly sales commission estimator — marginal tier table + unit bonus.

Rate table (authoritative — change here for demo tweaks):
  $0 – $100,000        @ 1%
  $100,001 – $250,000  @ 2%
  Above $250,000       @ 3%

Unit bonus: flat $1,000 when units_sold > 50.
"""
from dataclasses import dataclass
from typing import List


# (upper_exclusive, rate) — bracket width = upper_exclusive - previous upper
# First bracket: 0 to 100_000 at 1%
# Second: 100_000 to 250_000 at 2%  (width 150_000)
# Third: remainder at 3%
BRACKETS = [
    (100_000.0, 0.01, "$0 – $100,000"),
    (250_000.0, 0.02, "$100,001 – $250,000"),
    (None, 0.03, "Above $250,000"),
]

UNIT_BONUS_THRESHOLD = 50
UNIT_BONUS_AMOUNT = 1_000.0


@dataclass
class TierLine:
    bracket_label: str
    amount_in_bracket: float
    rate_pct: float
    commission: float


@dataclass
class MonthlyEstimateResult:
    sales_amount: float
    units_sold: int
    tier_lines: List[TierLine]
    tiered_commission: float
    unit_bonus: float
    total_payout: float
    explanation: List[str]


def compute_monthly_commission(sales_amount: float, units_sold: int) -> MonthlyEstimateResult:
    if sales_amount < 0:
        raise ValueError("sales_amount must be >= 0")
    if units_sold < 0:
        raise ValueError("units_sold must be >= 0")

    remaining = sales_amount
    prev_cap = 0.0
    tier_lines: List[TierLine] = []
    tiered_total = 0.0

    for cap, rate, label in BRACKETS:
        if remaining <= 0:
            amount_in_bracket = 0.0
        elif cap is None:
            amount_in_bracket = remaining
        else:
            bracket_width = cap - prev_cap
            amount_in_bracket = min(remaining, bracket_width)
            prev_cap = cap

        commission = round(amount_in_bracket * rate, 2)
        tier_lines.append(
            TierLine(
                bracket_label=label,
                amount_in_bracket=round(amount_in_bracket, 2),
                rate_pct=round(rate * 100, 2),
                commission=commission,
            )
        )
        tiered_total += commission
        remaining -= amount_in_bracket

    tiered_total = round(tiered_total, 2)
    unit_bonus = UNIT_BONUS_AMOUNT if units_sold > UNIT_BONUS_THRESHOLD else 0.0
    total_payout = round(tiered_total + unit_bonus, 2)

    explanation = []
    for line in tier_lines:
        if line.amount_in_bracket > 0:
            explanation.append(
                f"{line.rate_pct:.2f}% of ${line.amount_in_bracket:,.0f} "
                f"({line.bracket_label}) = ${line.commission:,.2f}."
            )
    if not any(l.amount_in_bracket > 0 for l in tier_lines):
        explanation.append("No sales entered — tiered commission is $0.00.")
    explanation.append(f"Tiered commission subtotal: ${tiered_total:,.2f}.")
    if unit_bonus > 0:
        explanation.append(
            f"Unit bonus: ${unit_bonus:,.0f} (units sold {units_sold} > {UNIT_BONUS_THRESHOLD})."
        )
    else:
        explanation.append(
            f"No unit bonus (units sold {units_sold} ≤ {UNIT_BONUS_THRESHOLD})."
        )
    explanation.append(f"Total estimated payout: ${total_payout:,.2f}.")

    return MonthlyEstimateResult(
        sales_amount=round(sales_amount, 2),
        units_sold=units_sold,
        tier_lines=tier_lines,
        tiered_commission=tiered_total,
        unit_bonus=unit_bonus,
        total_payout=total_payout,
        explanation=explanation,
    )
