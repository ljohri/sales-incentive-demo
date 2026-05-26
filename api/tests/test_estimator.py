"""Acceptance tests for monthly marginal commission estimator."""
import pytest

from app.estimator import compute_monthly_commission


def test_150k_sales_40_units_no_bonus():
    r = compute_monthly_commission(150_000, 40)
    assert r.tiered_commission == 2_000.0
    assert r.unit_bonus == 0.0
    assert r.total_payout == 2_000.0


def test_150k_sales_51_units_with_bonus():
    r = compute_monthly_commission(150_000, 51)
    assert r.tiered_commission == 2_000.0
    assert r.unit_bonus == 1_000.0
    assert r.total_payout == 3_000.0


def test_300k_sales_10_units():
    r = compute_monthly_commission(300_000, 10)
    assert r.tiered_commission == 5_500.0
    assert r.unit_bonus == 0.0
    assert r.total_payout == 5_500.0


def test_zero_sales():
    r = compute_monthly_commission(0, 0)
    assert r.tiered_commission == 0.0
    assert r.total_payout == 0.0


def test_exactly_50_units_no_bonus():
    r = compute_monthly_commission(100_000, 50)
    assert r.unit_bonus == 0.0


def test_boundary_100k_tier1_only():
    r = compute_monthly_commission(100_000, 0)
    assert r.tiered_commission == 1_000.0


def test_negative_sales_raises():
    with pytest.raises(ValueError):
        compute_monthly_commission(-1, 0)
