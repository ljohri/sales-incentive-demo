# Product specification — Sales Incentive Co-work Demo

**Version:** 1.1  
**Status:** Baseline ICM shipped; monthly estimator added in v1.1  
**Audience:** Developers evaluating agentic ICM integrations; sales reps using the estimator UI

---

## 1. Product overview

### 1.1 Vision

Provide a **small but credible** Incentive Compensation Management (ICM) surface that:

1. Powers a **Claude co-worker** via MCP over REST (quotas, plans, commissions, disputes, benchmarks).
2. Offers a **self-serve monthly commission estimator** so reps can model payout from sales dollars and units sold.

The product is a **reference implementation**, not production payroll software.

### 1.2 Product boundaries

| In scope | Out of scope |
|----------|--------------|
| Synthetic 5-year org + quarterly ICM APIs | Production SSO, RBAC, audit |
| MCP tools + `CLAUDE.md` agent skill | Custom NLP / chatbot framework |
| Monthly marginal tier estimator + web UI | Full comp statement PDF generation |
| Dockerized local run (Mac / Windows / Linux) | Multi-tenant SaaS hosting |

### 1.3 Users & journeys

**Journey A — Developer demo (agentic ICM)**  
Clone → `docker compose up` → configure MCP → ask Claude: *"What did Jordan earn in Q2?"* → observe tool chain.

**Journey B — Sales rep (monthly estimate)**  
Open web app → enter monthly sales + units → view tier breakdown and total → adjust inputs what-if style.

**Journey C — Comp ops dispute (agent)**  
*"Alex thinks their payout is wrong"* → agent pulls bookings, recomputes quarterly commission, may `flag_dispute`.

---

## 2. System context

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (rep)                             │
│              Monthly Commission Estimator (static UI)            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI (icm-api :8080)                        │
│  ┌──────────────────┐  ┌─────────────────────────────────────┐  │
│  │ /estimate/monthly│  │ ICM REST (reps, quota, commission…) │  │
│  └────────┬─────────┘  └──────────────────┬──────────────────┘  │
│           │ estimator.py                 │ SQLAlchemy            │
└───────────┼──────────────────────────────┼──────────────────────┘
            │                              │
            │ stateless                    ▼
            │                    ┌─────────────────┐
            │                    │  Postgres 16    │
            │                    │  (seeded org)   │
            └────────────────────┴─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Claude Desktop / Code / Cursor                                  │
│       MCP stdio ──► mcp_server/icm_mcp.py ──► REST (ICM only)   │
│       CLAUDE.md skill                                            │
└─────────────────────────────────────────────────────────────────┘
```

The **monthly estimator does not read Postgres** in v1.1; it is a pure calculation service co-located with the ICM API for demo simplicity.

---

## 3. Feature specification — ICM core (shipped)

### 3.1 Data entities

| Entity | Key fields | Relationships |
|--------|------------|---------------|
| Rep | employee_id, role, region, hire_date | 1:N quotas, bookings, commissions, disputes |
| IncentivePlan | role, effective dates, rates, accelerators | Referenced by Commission.plan_id |
| Quota | rep_id, period, quota_amount | Per rep per quarter |
| Booking | rep_id, period, amount, is_new_logo | Deal-level evidence |
| Commission | rep_id, period, tier breakdown (stored) | Snapshot per quarter |
| Dispute | rep_id, period, category, status | Workflow ticket |

See `api/app/models.py` and [PLANNING.md](PLANNING.md) for join semantics.

### 3.2 ICM API capabilities (summary)

| Capability | Endpoint | Notes |
|------------|----------|-------|
| List / resolve reps | `GET /reps`, `GET /reps/{rep}` | Name disambiguation → 409 |
| Quota attainment | `GET /quota-attainment` | Aggregates bookings for period |
| Plans | `GET /incentive-plans`, `GET /incentive-plans/for-rep/{rep}` | Role + date effective |
| Quarterly commission | `GET /commission` | Stored or `recompute=true` |
| Bookings | `GET /bookings` | Dispute evidence |
| Disputes | `POST /disputes`, `GET /disputes` | |
| Team benchmark | `GET /team-benchmark` | Median / top decile |

Quarterly commission uses **quota-relative accelerators** (100% / 120% brackets) — distinct from the **monthly dollar-tier** estimator in §4.

### 3.3 MCP tools

Nine tools in `mcp_server/icm_mcp.py` map 1:1 to ICM REST paths. Agent behavior is specified in `CLAUDE.md`.

---

## 4. Feature specification — Monthly commission estimator (v1.1)

### 4.1 Purpose

Allow a rep to answer: *"If I sell $X this month and move Y units, what is my estimated commission?"* without waiting for quarterly ICM batch jobs.

### 4.2 Inputs

| Field | Type | Validation | UI label |
|-------|------|------------|----------|
| `sales_amount` | number (USD) | ≥ 0, finite | Monthly sales ($) |
| `units_sold` | integer | ≥ 0 | Units sold |

### 4.3 Tiered commission algorithm (marginal)

**Brackets** (on cumulative monthly sales `S`):

| Bracket index | Sales in bracket | Rate |
|---------------|------------------|------|
| 1 | $0 up to $100,000 | 1.00% |
| 2 | $100,000.01 up to $250,000 | 2.00% |
| 3 | Above $250,000 | 3.00% |

**Algorithm:**

```
remaining = S
commission = 0
for each bracket (cap, rate):
    amount_in_bracket = min(remaining, bracket_width)
    commission += amount_in_bracket * rate
    remaining -= amount_in_bracket
```

**Worked example — S = $150,000**

| Bracket | Amount in bracket | Rate | Commission |
|---------|-------------------|------|------------|
| 1 | $100,000 | 1% | $1,000 |
| 2 | $50,000 | 2% | $1,000 |
| 3 | $0 | 3% | $0 |
| **Subtotal** | | | **$2,000** |

**Worked example — S = $300,000**

| Bracket | Amount in bracket | Rate | Commission |
|---------|-------------------|------|------------|
| 1 | $100,000 | 1% | $1,000 |
| 2 | $150,000 | 2% | $3,000 |
| 3 | $50,000 | 3% | $1,500 |
| **Subtotal** | | | **$5,500** |

### 4.4 Unit volume bonus

```
unit_bonus = 1000 if units_sold > 50 else 0
total_payout = tiered_commission + unit_bonus
```

| units_sold | unit_bonus |
|------------|------------|
| 50 | $0 |
| 51 | $1,000 |

Not prorated; threshold is strict greater-than 50.

### 4.5 Outputs

| Field | Description |
|-------|-------------|
| `sales_amount` | Echo input |
| `units_sold` | Echo input |
| `tier_lines[]` | `{ bracket_label, amount_in_bracket, rate_pct, commission }` |
| `tiered_commission` | Sum of tier lines |
| `unit_bonus` | $0 or $1,000 |
| `total_payout` | tiered_commission + unit_bonus |
| `explanation[]` | Human-readable strings for UI |

### 4.6 API contract

**`POST /estimate/monthly`**

Request body:

```json
{
  "sales_amount": 150000,
  "units_sold": 51
}
```

Response `200`:

```json
{
  "sales_amount": 150000,
  "units_sold": 51,
  "tier_lines": [
    {
      "bracket_label": "$0 – $100,000",
      "amount_in_bracket": 100000,
      "rate_pct": 1.0,
      "commission": 1000.0
    },
    {
      "bracket_label": "$100,001 – $250,000",
      "amount_in_bracket": 50000,
      "rate_pct": 2.0,
      "commission": 1000.0
    }
  ],
  "tiered_commission": 2000.0,
  "unit_bonus": 1000.0,
  "total_payout": 3000.0,
  "explanation": ["..."]
}
```

Errors: `422` validation (negative values), `400` if business rules extended later.

### 4.7 Web UI

| Element | Behavior |
|---------|----------|
| Route | `GET /` serves `static/index.html` |
| Form | Sales + units; Calculate button |
| Results panel | Table of tiers; bonus line; total highlighted |
| API call | `fetch('/estimate/monthly', { method: 'POST', ... })` |

Styling: clean, professional, works in Chrome/Safari/Edge on desktop.

### 4.8 Change showcase (developer narrative)

To change rates for a live demo:

1. Edit bracket definitions in `api/app/estimator.py` (single source of truth).
2. Optionally update labels in `api/app/static/index.html`.
3. Rebuild API container: `docker compose up --build -d api`.

No MCP or database migration required for rate-table tweaks.

---

## 5. Security & privacy (demo level)

| Topic | v1.1 approach |
|-------|----------------|
| Auth | None on estimator; ICM APIs open on localhost |
| Data | Estimator stateless; ICM uses synthetic data |
| Transport | HTTP localhost only in docs |

Production hardening is explicitly out of scope.

---

## 6. Success metrics (demo)

| Metric | Target |
|--------|--------|
| Time to first `docker compose up` | < 5 min for experienced dev |
| Estimator vs API consistency | 100% match for acceptance cases in REQUIREMENTS.md |
| Agent demo prompts | 5 scripted prompts in README work with MCP |

---

## 7. Related documents

| Document | Purpose |
|----------|---------|
| [REQUIREMENTS.md](REQUIREMENTS.md) | Requirement IDs and acceptance criteria |
| [BUILD_PLAN.md](BUILD_PLAN.md) | Phased delivery plan |
| [PLANNING.md](PLANNING.md) | Agent orchestration vs SQL joins |
| [README.md](../README.md) | Setup and runbook |
| [CLAUDE.md](../CLAUDE.md) | Agent skill file |
