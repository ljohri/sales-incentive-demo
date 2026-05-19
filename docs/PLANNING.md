# Agent planning & data joins

This document explains how **multi-step planning** works in the Sales Incentive Co-work demo: what Claude orchestrates via MCP tools versus what the FastAPI backend joins in Postgres.

There are **two layers** of "planning"—only one of them runs SQL joins.

| Layer | Who | What it looks like |
|--------|-----|-------------------|
| **Agent planning** | Claude, guided by `CLAUDE.md` | A chain of MCP tool calls: resolve rep → quota → plan → commission → (optional) bookings / dispute |
| **Data joining** | FastAPI in each endpoint | Queries filtered on `rep_id` + `period` (and `role` + dates for plans). One endpoint uses an explicit SQL `JOIN`. |

The agent does **not** write SQL. Each MCP tool is a thin HTTP wrapper (`mcp_server/icm_mcp.py` → REST). Join correctness lives in `api/app/main.py`.

---

## Data model (what should be linked)

From `api/app/models.py`:

```
reps
  ├── quotas          (rep_id, period)
  ├── bookings        (rep_id, period)
  ├── commissions     (rep_id, period) ──FK──► incentive_plans (plan_id)
  └── disputes        (rep_id, period)

incentive_plans       (role, effective_start, effective_end)
       ▲
       └── linked to rep only by ROLE + date range (no rep_id FK)
```

**Important:** `Rep` has no foreign key to `IncentivePlan`. Plan assignment is:

- `IncentivePlan.role == Rep.role`
- Quarter start date within `[effective_start, effective_end]`

That matches many real ICM systems (role-based plans). "Join rep to plan" is a **semantic** join, not a single FK hop.

---

## What each API endpoint joins

### `GET /quota-attainment`

1. Resolve `Rep` (by employee_id, email, or name)
2. Load `Quota` for `(rep_id, period)`
3. Aggregate `Booking` for `(rep_id, period)`

**Join key:** same `rep_id` + `period` on `quotas` and `bookings`. Attainment = `sum(bookings) / quota`.

### `GET /commission` (consolidated path)

In **one** request the API:

1. Resolves `Rep`
2. Loads `Quota` for `(rep_id, period)`
3. Loads `IncentivePlan` for `(rep.role, period_start in plan window)`
4. Returns stored `Commission` **or** reloads `Booking` rows and recomputes (`recompute=true`)

**Join keys:**

- `rep + period` → quota and bookings
- `rep.role + period` → plan
- `rep + period` → stored commission (includes `plan_id` FK)

Commission math in `api/app/logic.py` applies plan rates to quota/bookings buckets.

### `GET /team-benchmark`

Explicit SQL join:

```python
db.query(Commission, Rep).join(Rep, Rep.id == Commission.rep_id)
```

Uses the **denormalized** `commissions` snapshot (`bookings_total`, `quota_amount`, `attainment_pct`). Does not join `quotas` or `bookings` at query time. Optional filters on `Rep.role` and `Rep.region`.

### `GET /bookings`, `GET /disputes`

Filter by `rep_id` (+ optional `period`). No cross-table join.

---

## Agent multi-step plans (orchestration)

`CLAUDE.md` teaches **orchestration for the demo audience**, not because the database requires four round trips.

### Example: "What did Jordan earn in Q2?"

| Step | Tool | Tables (via API) |
|------|------|------------------|
| 1 | Resolve rep | `reps` |
| 2 | Quota vs bookings | `quotas` + `bookings` |
| 3 | Plan tiers | `incentive_plans` (via `rep.role` + date) |
| 4 | Payout | `commissions` or recompute from `bookings` |

**Minimum correct path:** one `calculate_commission` call (steps 1–4 already inside `/commission`).

**Demo path:** `get_quota_attainment` + `get_incentive_plan` + `calculate_commission` so the audience sees the reasoning chain.

Extra steps are for **transparency** and **teaching**, not because joins are missing server-side.

### When multiple tool calls are required

| Question | Pattern | Why |
|----------|---------|-----|
| Rank all reps by attainment | `list_reps` → N × `get_quota_attainment` | No batch leaderboard endpoint |
| Closest to next accelerator | Fan-out `get_quota_attainment` | Per-rep % vs 100% / 120% bands |
| West vs East in Q4 | 2 × `get_team_benchmark` | One call per region filter |
| Payout dispute | `list_bookings` + `calculate_commission(recompute=true)` | Deal-level evidence + validation |

The agent correlates results in memory using **`employee_id` / name** and **`period`**. Every call in a chain must use the **same period** (e.g. `2024Q2`, not mixed formats).

---

## Correctness checklist

### What is correct

- Grain `(rep_id, period)` for quota, bookings, commission, disputes
- Plan lookup by `role` + quarter start date
- `Commission.plan_id` matches the plan used at seed/compute time
- Team benchmark: `commissions` ↔ `reps` for role/region filters

### Caveats

1. **Historical plan vs today**  
   `get_incentive_plan(rep, as_of)` defaults `as_of` to **today**. For past quarters, pass `as_of` = first day of that quarter (e.g. `2024-04-01` for `2024Q2`), or rely on `calculate_commission`, which already resolves the plan for that period.

2. **Redundant attainment**  
   `get_quota_attainment` and `calculate_commission` should agree unless you use `recompute=true` vs stored snapshot.

3. **Kicker explanation (stored path)**  
   When returning stored commission, the API backs out new-logo bookings from `kicker_commission / kicker_rate` for the explanation text—not a second query to `bookings`.

4. **No cross-rep crediting in data**  
   "Deal credited to wrong rep" disputes are workflow-only; there is no join from one rep's booking to another's quota.

---

## Sequence: demo vs minimal path

```mermaid
sequenceDiagram
    participant User
    participant Agent as Claude (CLAUDE.md)
    participant MCP as MCP tools
    participant API as FastAPI
    participant DB as Postgres

    User->>Agent: What did Jordan earn in Q2 2024?
    Note over Agent: Demo: 3–4 tools; Minimal: 1 tool

    Agent->>MCP: get_quota_attainment(Jordan, 2024Q2)
    MCP->>API: GET /quota-attainment
    API->>DB: reps + quotas + aggregate(bookings)

    Agent->>MCP: get_incentive_plan(Jordan, as_of?)
    MCP->>API: GET /incentive-plans/for-rep/...
    API->>DB: reps + incentive_plans by role+date

    Agent->>MCP: calculate_commission(Jordan, 2024Q2)
    MCP->>API: GET /commission
    API->>DB: reps + quotas + plans + commissions OR bookings
    API-->>Agent: breakdown + explanation[]

    Agent->>User: Narrative + tier math
```

---

## Summary

| Question | Answer |
|----------|--------|
| Are SQL joins correct? | Yes, for this schema: `(rep_id, period)`; plans via `(role, effective dates)`; benchmarks via `commissions` ⋈ `reps`. |
| Is the agent doing SQL joins? | No—it orchestrates tools and stitches JSON by shared keys. |
| Is multi-step always needed? | No—`/commission` consolidates rep + quota + plan + payout. Multi-step is often for demo narrative or missing batch APIs. |
| Main footgun | `get_incentive_plan` without historical `as_of` while discussing a past quarter. |

See also: [`CLAUDE.md`](../CLAUDE.md) (agent behavior), [`README.md`](../README.md) (setup), [`api/app/main.py`](../api/app/main.py) (endpoint implementation).
