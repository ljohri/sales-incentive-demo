from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class RepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    role: str
    region: str
    territory: str
    hire_date: date
    active: bool


class IncentivePlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    plan_name: str
    effective_start: date
    effective_end: Optional[date]
    base_salary: float
    on_target_variable: float
    commission_rate: float
    accelerator_100: float
    accelerator_120: float
    kicker_new_logo: float
    notes: Optional[str]


class QuotaAttainment(BaseModel):
    rep_id: int
    employee_id: str
    name: str
    role: str
    region: str
    period: str
    quota: float
    bookings: float
    attainment_pct: float
    deals: int


class CommissionBreakdown(BaseModel):
    rep_id: int
    employee_id: str
    name: str
    role: str
    period: str
    plan_name: str
    bookings_total: float
    quota_amount: float
    attainment_pct: float
    base_commission: float
    accelerator_commission: float
    kicker_commission: float
    total_commission: float
    explanation: List[str]


class DisputeIn(BaseModel):
    rep_employee_id: str = Field(..., description="employee_id of the rep")
    period: str = Field(..., description="e.g. 2024Q2")
    category: str = Field(..., description="quota | crediting | accelerator | other")
    summary: str
    details: Optional[str] = None
    amount_in_dispute: float = 0.0


class DisputeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: str
    rep_id: int
    period: str
    category: str
    summary: str
    details: Optional[str]
    amount_in_dispute: float
    status: str
    opened_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]


class TeamBenchmark(BaseModel):
    period: str
    role: Optional[str]
    region: Optional[str]
    rep_count: int
    quota_total: float
    bookings_total: float
    attainment_median_pct: float
    attainment_top_decile_pct: float
    attainment_mean_pct: float
    top_performer: Optional[str]
    bottom_performer: Optional[str]
