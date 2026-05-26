# Requirements — Sales Incentive Co-work Demo

This document captures **functional and non-functional requirements** for the
repository: the existing ICM agentic demo plus the **monthly commission
estimator** web app enhancement.

---

## 1. Stakeholders & goals

| Stakeholder | Goal |
|-------------|------|
| **Sales rep** | Estimate monthly commission from sales volume and units sold before payroll closes. |
| **Developer / audience** | Clone the repo, run Docker, wire MCP, and see Claude reason over ICM APIs. |
| **Comp ops (demo)** | Illustrate disputes, plans, quotas, and benchmarks via agent tools. |

**Primary demo goal:** Show that a real ICM-style backend + MCP + `CLAUDE.md` skill
can power a natural-language co-worker—and that product changes (e.g. a new
estimator) can be added with small, localized diffs.

---

## 2. Existing system (baseline — implemented)

### R1 — Containerized ICM backend

- **R1.1** Postgres 16 and FastAPI API run via `docker compose up`.
- **R1.2** Idempotent seeder loads 20 reps, 5 years of quarterly data (`2021Q1`–`2025Q4`).
- **R1.3** REST endpoints: reps, plans, quota attainment, commission, bookings, disputes, team benchmark.

### R2 — MCP agent surface

- **R2.1** MCP server exposes 9 tools wrapping the REST API (stdio transport).
- **R2.2** `CLAUDE.md` defines agent behavior, comp formula, and demo prompt patterns.

### R3 — Cross-platform developer experience

- **R3.1** README documents macOS, Linux, and Windows setup.
- **R3.2** No cloud dependency required to run the backend.

---

## 3. Monthly commission estimator (new)

### R4 — Tiered (marginal) commission on monthly sales

| ID | Requirement | Priority |
|----|-------------|----------|
| **R4.1** | Rep enters **monthly sales amount** (currency, ≥ 0). | Must |
| **R4.2** | System applies a **three-tier rate table** using **marginal** (bracket) logic: each rate applies only to the portion of sales within that tier, not to the full amount. | Must |
| **R4.3** | Tier definitions: **0–$100K @ 1%**, **$100K–$250K @ 2%**, **above $250K @ 3%**. | Must |
| **R4.4** | Example: sales = **$150K** → commission = **1% × $100K + 2% × $50K** = **$1,000 + $1,000 = $2,000** (before unit bonus). | Must |
| **R4.5** | Response includes a **line-by-line breakdown** per tier (amount in bracket, rate, commission for bracket). | Should |

**Rate table (authoritative):**

| Sales range (monthly) | Commission % |
|----------------------|--------------|
| $0 – $100,000 | 1% |
| $100,001 – $250,000 | 2% |
| Above $250,000 | 3% |

*Note: Upper bound of tier N is exclusive start of tier N+1; implementation uses bracket widths on cumulative sales.*

### R5 — Units sold & volume bonus

| ID | Requirement | Priority |
|----|-------------|----------|
| **R5.1** | Rep enters **number of units sold** in the month (integer, ≥ 0). | Must |
| **R5.2** | If units sold **> 50**, add a **flat bonus of $1,000** to total payout. | Must |
| **R5.3** | If units ≤ 50, unit bonus = **$0** (bonus is not prorated). | Must |
| **R5.4** | Total estimated payout = **tiered commission + unit bonus**. | Must |

### R6 — Web application (rep-facing)

| ID | Requirement | Priority |
|----|-------------|----------|
| **R6.1** | Browser UI served from the same stack (no separate deploy required for demo). | Must |
| **R6.2** | Form fields: **Sales amount**, **Units sold**, **Calculate** action. | Must |
| **R6.3** | Display: tier breakdown, unit bonus line, **total estimated commission**. | Must |
| **R6.4** | Client-side validation: non-negative numbers; clear error messages. | Should |
| **R6.5** | UI is readable on desktop (responsive nice-to-have). | Should |

### R7 — API for estimator (supports UI & future agents)

| ID | Requirement | Priority |
|----|-------------|----------|
| **R7.1** | HTTP endpoint accepts `sales_amount` and `units_sold`, returns JSON breakdown. | Must |
| **R7.2** | Calculation logic lives in a **dedicated module** (testable, easy to change rates). | Must |
| **R7.3** | Invalid input returns **4xx** with message (negative sales, non-integer units). | Should |

---

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| **NFR1** | Estimator works with `docker compose up` without extra steps. |
| **NFR2** | Rate table changes should require editing one module + optional UI labels (showcase “easy enhancement”). |
| **NFR3** | MIT license; suitable for public GitHub. |
| **NFR4** | No PII required for estimator (stateless calculation). |

---

## 5. Out of scope (this phase)

- Authentication / per-rep identity on the estimator page.
- Persisting estimator runs to the database.
- Replacing quarterly ICM commission logic with the monthly tier table (estimator is **separate** from quarterly `calculate_commission`).
- Payroll export, tax withholding, or draw recovery.

---

## 6. Acceptance criteria (estimator)

1. Open `http://localhost:8080/` → see commission estimator form.
2. Enter sales **150000**, units **40** → tier commission **$2,000**, unit bonus **$0**, total **$2,000**.
3. Same sales, units **51** → total **$3,000** ($2,000 + $1,000 bonus).
4. Enter sales **300000**, units **10** → 1%×100k + 2%×150k + 3%×50k = **$6,500** commission, no unit bonus.
5. `POST /estimate/monthly` (or documented path) returns same numbers as UI.

---

## 7. Traceability

| Requirement | Spec section | Implementation |
|-------------|--------------|----------------|
| R4.x | PRODUCT_SPEC § Estimator | `api/app/estimator.py`, `main.py` |
| R5.x | PRODUCT_SPEC § Unit bonus | `api/app/estimator.py` |
| R6.x | PRODUCT_SPEC § Web UI | `api/app/static/` |
| R7.x | PRODUCT_SPEC § API | `POST /estimate/monthly` |
