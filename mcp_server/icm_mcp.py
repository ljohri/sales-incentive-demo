"""ICM MCP server.

Wraps the local ICM REST API as MCP tools so Claude (Desktop / Code / Cursor)
can call them as an agentic co-worker.

Run (stdio transport — default for Claude desktop integrations):

    ICM_API_URL=http://localhost:8080 python icm_mcp.py

Tools exposed:
    - list_reps
    - get_quota_attainment
    - get_incentive_plan
    - calculate_commission
    - flag_dispute
    - list_disputes
    - get_team_benchmark
    - list_bookings
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("ICM_API_URL", "http://localhost:8080").rstrip("/")

mcp = FastMCP("icm-demo")


def _get(path: str, **params) -> dict | list:
    clean = {k: v for k, v in params.items() if v is not None}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{API_URL}{path}", params=clean)
        r.raise_for_status()
        return r.json()


def _post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=15.0) as client:
        r = client.post(f"{API_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


@mcp.tool()
def list_reps(role: Optional[str] = None, region: Optional[str] = None) -> list:
    """List sales reps in the org, optionally filtered by role (SDR | AE | EAE)
    or region (West | Central | East | South).
    """
    return _get("/reps", role=role, region=region)


@mcp.tool()
def get_quota_attainment(rep: str, period: str) -> dict:
    """Fetch quota, total bookings, and attainment % for a rep in a given quarter.

    Args:
        rep: employee_id (e.g. E1003), email, or 'First Last' name.
        period: Quarter string like '2024Q2'.
    """
    return _get("/quota-attainment", rep=rep, period=period)


@mcp.tool()
def get_incentive_plan(rep: str, as_of: Optional[str] = None) -> dict:
    """Return the active incentive comp plan for a rep, including base, OTE,
    commission rate, accelerator tiers, and new-logo kicker.

    Args:
        rep: employee_id, email, or 'First Last'.
        as_of: Optional ISO date (YYYY-MM-DD); defaults to today.
    """
    return _get(f"/incentive-plans/for-rep/{rep}", as_of=as_of)


@mcp.tool()
def list_incentive_plans(role: Optional[str] = None, as_of: Optional[str] = None) -> list:
    """List incentive plans, optionally filtered by role and effective date."""
    return _get("/incentive-plans", role=role, as_of=as_of)


@mcp.tool()
def calculate_commission(rep: str, period: str, recompute: bool = False) -> dict:
    """Compute commission for a rep in a quarter. Returns the full tiered
    breakdown (base, accelerator, kicker) plus a human-readable explanation.

    Args:
        rep: employee_id, email, or 'First Last'.
        period: e.g. '2024Q2'.
        recompute: If true, recompute live from bookings instead of returning
            the stored quarterly snapshot. Useful when investigating disputes.
    """
    return _get("/commission", rep=rep, period=period, recompute=recompute)


@mcp.tool()
def flag_dispute(
    rep_employee_id: str,
    period: str,
    category: str,
    summary: str,
    details: Optional[str] = None,
    amount_in_dispute: float = 0.0,
) -> dict:
    """Open a payout dispute ticket on behalf of a rep.

    Args:
        rep_employee_id: Required employee_id (e.g. E1003).
        period: e.g. '2024Q2'.
        category: One of 'quota', 'crediting', 'accelerator', 'other'.
        summary: One-line summary.
        details: Optional longer explanation / supporting context.
        amount_in_dispute: Dollar amount in dispute (best estimate).
    """
    return _post(
        "/disputes",
        {
            "rep_employee_id": rep_employee_id,
            "period": period,
            "category": category,
            "summary": summary,
            "details": details,
            "amount_in_dispute": amount_in_dispute,
        },
    )


@mcp.tool()
def list_disputes(
    rep: Optional[str] = None,
    period: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    """List disputes, optionally filtered by rep, period, or status
    (open | in_review | resolved | rejected).
    """
    return _get("/disputes", rep=rep, period=period, status=status)


@mcp.tool()
def get_team_benchmark(
    period: str,
    role: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """Compare team-wide performance for a quarter. Returns median, top-decile,
    and mean attainment, plus the top and bottom performers.

    Useful when a rep asks how they stack up.
    """
    return _get("/team-benchmark", period=period, role=role, region=region)


@mcp.tool()
def list_bookings(rep: str, period: Optional[str] = None) -> list:
    """Pull the underlying deals booked by a rep. Use this when investigating
    a dispute or showing the agent's reasoning chain (deal-level evidence).
    """
    return _get("/bookings", rep=rep, period=period)


if __name__ == "__main__":
    mcp.run()
