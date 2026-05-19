from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from .db import Base


class Rep(Base):
    __tablename__ = "reps"

    id = Column(Integer, primary_key=True)
    employee_id = Column(String(16), unique=True, nullable=False, index=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    role = Column(String(32), nullable=False)  # SDR | AE | EAE
    region = Column(String(32), nullable=False)  # West | Central | East | South
    territory = Column(String(64), nullable=False)
    hire_date = Column(Date, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    quotas = relationship("Quota", back_populates="rep", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="rep", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="rep", cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="rep", cascade="all, delete-orphan")


class IncentivePlan(Base):
    """A role-level comp plan that applies for a date range."""
    __tablename__ = "incentive_plans"

    id = Column(Integer, primary_key=True)
    role = Column(String(32), nullable=False, index=True)
    plan_name = Column(String(128), nullable=False)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)

    base_salary = Column(Float, nullable=False)
    on_target_variable = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)  # of bookings up to 100%
    accelerator_100 = Column(Float, nullable=False, default=1.0)  # multiplier 100-120%
    accelerator_120 = Column(Float, nullable=False, default=1.0)  # multiplier >120%
    kicker_new_logo = Column(Float, nullable=False, default=0.0)  # bonus rate on new logo bookings
    notes = Column(Text, nullable=True)


class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Integer, primary_key=True)
    rep_id = Column(Integer, ForeignKey("reps.id"), nullable=False, index=True)
    period = Column(String(8), nullable=False, index=True)  # e.g. 2024Q2
    period_year = Column(Integer, nullable=False, index=True)
    period_quarter = Column(Integer, nullable=False)
    quota_amount = Column(Float, nullable=False)

    rep = relationship("Rep", back_populates="quotas")


class Booking(Base):
    """A closed-won deal booked by a rep."""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    rep_id = Column(Integer, ForeignKey("reps.id"), nullable=False, index=True)
    deal_id = Column(String(24), unique=True, nullable=False)
    account = Column(String(128), nullable=False)
    booked_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    period = Column(String(8), nullable=False, index=True)
    is_new_logo = Column(Boolean, default=False, nullable=False)

    rep = relationship("Rep", back_populates="bookings")


class Commission(Base):
    """Pre-computed quarterly commission record per rep."""
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True)
    rep_id = Column(Integer, ForeignKey("reps.id"), nullable=False, index=True)
    period = Column(String(8), nullable=False, index=True)
    bookings_total = Column(Float, nullable=False)
    quota_amount = Column(Float, nullable=False)
    attainment_pct = Column(Float, nullable=False)
    base_commission = Column(Float, nullable=False)
    accelerator_commission = Column(Float, nullable=False)
    kicker_commission = Column(Float, nullable=False)
    total_commission = Column(Float, nullable=False)
    plan_id = Column(Integer, ForeignKey("incentive_plans.id"), nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rep = relationship("Rep", back_populates="commissions")
    plan = relationship("IncentivePlan")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(String(24), unique=True, nullable=False, index=True)
    rep_id = Column(Integer, ForeignKey("reps.id"), nullable=False, index=True)
    period = Column(String(8), nullable=False, index=True)
    category = Column(String(32), nullable=False)  # quota | crediting | accelerator | other
    summary = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    amount_in_dispute = Column(Float, nullable=False, default=0.0)
    status = Column(String(16), nullable=False, default="open")  # open | in_review | resolved | rejected
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    rep = relationship("Rep", back_populates="disputes")
