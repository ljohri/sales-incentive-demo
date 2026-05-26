# Query catalog — supported questions & prompts

This document lists the **full range of queries** the Sales Incentive Co-work demo can
answer, grouped by channel and topic. Use it to script demos, test the agent, or map
your own ICM APIs to natural-language patterns.

**Data window:** quarters `2021Q1` through `2025Q4` · **20 reps** · roles `SDR`, `AE`, `EAE` ·
regions `West`, `Central`, `East`, `South`.

**Rep identifiers** (ICM tools): `employee_id` (e.g. `E1003`), email, or `"First Last"`.
First-name-only lookup works when unique; otherwise the API returns **409** with candidates.

**Period format:** `YYYYQn` (e.g. `2024Q2`). Variants like `Q2 2024` or `q2 2024` should be
normalized before calling tools.

---

## How to run queries

| Channel | Best for | Entry point |
|---------|----------|-------------|
| **Claude + MCP** | Agentic multi-step reasoning, disputes, leaderboards | Wire `icm-demo` MCP server; see root `README.md` |
| **REST API** | Scripts, integrations, Swagger | `http://localhost:8080/docs` |
| **Web UI** | Monthly commission **estimator** only (marginal tiers + unit bonus) | `http://localhost:8080/` |
| **Direct SQL** | Not supported | Use API only |

---

## 1. Org discovery & rep lookup

### Natural-language examples

- Who are all the sales reps?
- List every AE in the West region.
- Show me all enterprise AEs (`EAE`).
- How many reps do we have by role?
- Find rep `E1002` / `priya.anderson@example.com` / `Priya Anderson`.
- Who works in the Northeast territory?
- Which reps were hired in 2022?

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| List / filter org | `list_reps` | `role?`, `region?` |
| Single rep profile | *(via attainment/commission)* or `GET /reps/{rep}` | `rep` |

### REST

- `GET /reps` — optional `role`, `region`
- `GET /reps/{rep}` — resolve one rep

### Notes

- Territory and hire date are on the rep record but there is **no dedicated MCP tool**; use `list_reps` and filter in the agent, or `GET /reps`.
- Rep names in the seeded data are synthetic (e.g. Jordan, Alex, Priya); use `list_reps` if unsure who exists.

---

## 2. Quota & attainment (quarterly)

### Natural-language examples

- Where is **Jordan** against quota in **2024Q2**?
- What was **Priya’s** attainment last quarter?
- How much did **Alex** book in **2025Q1** vs their quota?
- How many deals did **E1003** close in **2024Q4**?
- Is **Marcus** above or below 100% attainment in **2023Q3**?
- What’s **Jordan’s** quota amount for **2024Q2**? (East/West reps have ~5% uplift.)

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Quota, bookings, attainment %, deal count | `get_quota_attainment` | `rep`, `period` |

### REST

- `GET /quota-attainment?rep=&period=`

### Derived questions (agent computes from tool output)

- How far is rep X from 100% quota?
- How far from 120% quota?
- What dollar gap to the next accelerator threshold?

---

## 3. Incentive plans & comp design

### Natural-language examples

- What comp plan is **Jordan** on today?
- What plan applied to **Priya** in **2024Q2**? *(use `as_of=2024-04-01` on plan tool)*
- What is the commission rate and accelerators for an **AE**?
- Compare the **2021 AE plan** vs the **2024 AE plan**.
- List all incentive plans for **SDR** role.
- What is the new-logo kicker for **enterprise AEs**?
- What’s **Jordan’s** base salary and OTE variable?

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Active plan for one rep | `get_incentive_plan` | `rep`, `as_of?` (ISO date) |
| Browse / compare plans | `list_incentive_plans` | `role?`, `as_of?` |

### REST

- `GET /incentive-plans/for-rep/{rep}?as_of=`
- `GET /incentive-plans?role=&as_of=`

### Notes

- Plans are **role-based**, not per-rep FK. Historical quarters need **`as_of`** set to a date in that quarter.
- Plan refresh in **2024** affects rates, accelerators, and kickers.

---

## 4. Quarterly commission & payout breakdown

### Natural-language examples

- What did **Jordan earn in Q2 2024**?
- Break down **Priya’s** commission for **2025Q1** tier by tier.
- How much accelerator pay did **Alex** get in **2024Q4**?
- What was the new-logo kicker for **E1002** in **2024Q2**?
- Recompute **Marcus’s** payout for **2023Q2** from raw bookings.
- Why is **Jordan’s** commission $X? *(agent uses `explanation[]` from API)*
- Base vs accelerator vs kicker for rep X in period Y.

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Stored payout + explanation | `calculate_commission` | `rep`, `period`, `recompute=false` |
| Live recompute from deals | `calculate_commission` | `rep`, `period`, `recompute=true` |

### REST

- `GET /commission?rep=&period=&recompute=`

### Commission model (quarterly ICM)

- Base on bookings up to 100% of quota × `commission_rate`
- Accelerator 100–120% of quota × rate × `accelerator_100`
- Above 120% × rate × `accelerator_120`
- New-logo kicker on flagged bookings

*This is **not** the same as the monthly marginal dollar-tier estimator (§10).*

---

## 5. Deal-level evidence (bookings)

### Natural-language examples

- Show all deals **Jordan** booked in **2024Q2**.
- Which of **Priya’s** deals in **2025Q1** were new logo?
- List bookings for **Alex** (all time or by quarter).
- What accounts did **E1017** close in **2024Q4**?
- Total and count of deals for rep X in period Y *(often paired with dispute investigation)*.

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Deal list | `list_bookings` | `rep`, `period?` |

### REST

- `GET /bookings?rep=&period=`

---

## 6. Team & regional benchmarks

### Natural-language examples

- How did the team perform in **2024Q4**?
- What’s the median attainment for **AEs** in **2025Q1**?
- How did the **West** region stack up vs **East** in **2024Q4**?
- Who was the top performer in **2024Q3** for all reps?
- Who’s the bottom performer among **SDRs** in **2022Q4**?
- What’s the top-decile attainment for **Central** in **2024Q2**?
- Total team quota and bookings for **2025Q2**.

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Aggregated team stats | `get_team_benchmark` | `period`, `role?`, `region?` |

### REST

- `GET /team-benchmark?period=&role=&region=`

### Comparative patterns (typically 2+ tool calls)

- West vs East → two `get_team_benchmark` calls, same `period`, different `region`
- AE vs EAE → two calls, different `role`
- Role vs company-wide → one filtered, one unfiltered

---

## 7. Leaderboards & ranking (agent fan-out)

No single “leaderboard” API — the agent uses **`list_reps`** + N × **`get_quota_attainment`**
(or reads attainment from commission/benchmark data).

### Natural-language examples

- Rank all reps by attainment in **2024Q4**.
- Who are the top 5 performers this quarter?
- Who’s at the bottom of the leaderboard for **2025Q1**?
- Rank only **AEs** by attainment in **2024Q2**.
- Rank **West** region reps by bookings in **2024Q3**.

### Typical tool chain

1. `list_reps` (optional `role` / `region` filter)
2. Parallel `get_quota_attainment` per rep for `period`
3. Sort by `attainment_pct` or `bookings` in the agent

---

## 8. Accelerator proximity & pipeline coaching

### Natural-language examples

- Who’s closest to their **next accelerator** this quarter?
- Which reps are between **90% and 100%** of quota?
- Who just crossed **120%** attainment?
- How many reps are in the 100–120% accelerator band in **2024Q4**?
- How much more does **Jordan** need to hit 100% quota in **2025Q2**?

### Typical tool chain

1. `list_reps` (or filter by team)
2. Fan-out `get_quota_attainment` for current/target `period`
3. Agent filters bands (90–100%, 100–120%, 110–120%, etc.) and ranks by distance to threshold

Alternative: `get_team_benchmark` for headline stats, then drill into individuals.

---

## 9. Disputes — investigation & filing

### Natural-language examples

- **Alex thinks their payout is wrong** — help me investigate.
- Open a dispute for **E1002** for **2024Q2** — crediting issue on Acme deal.
- List all **open** disputes.
- What disputes does **Priya** have?
- Show resolved disputes for **2023Q4**.
- File a dispute: quota too high, ~$12K in dispute, period **2024Q1**.
- What’s ticket **DISP-00005**? *(list + filter by rep/period)*

### MCP tools

| Query intent | Tool | Parameters |
|--------------|------|------------|
| Investigate payout | `list_bookings` + `calculate_commission` | `recompute=true` |
| Open ticket | `flag_dispute` | `rep_employee_id`, `period`, `category`, `summary`, `details?`, `amount_in_dispute` |
| List tickets | `list_disputes` | `rep?`, `period?`, `status?` |

### REST

- `POST /disputes`
- `GET /disputes?rep=&period=&status=`

### Categories

`quota` · `crediting` · `accelerator` · `other`

### Status values

`open` · `in_review` · `resolved` · `rejected`

### Rules

- Agent should **investigate** (bookings + commission) before `flag_dispute`.
- `flag_dispute` requires **`rep_employee_id`** (not first name alone).
- Cross-rep crediting is **not** modeled in data—disputes are workflow records only.

---

## 10. Monthly commission estimator (web + REST only)

**Not exposed via MCP** in v1.1. Reps use the browser or `POST /estimate/monthly`.

### User inputs

- Monthly **sales amount** ($)
- **Units sold** (integer)

### Rate table (marginal / bracket)

| Sales range (monthly) | Rate |
|----------------------|------|
| $0 – $100,000 | 1% |
| $100,001 – $250,000 | 2% |
| Above $250,000 | 3% |

Each rate applies only to the portion of sales **in that bracket** (not blended on full amount).

**Unit bonus:** **$1,000** if `units_sold > 50`; otherwise $0.

### Natural-language examples (human → UI, or future agent tool)

- If I sell **$150,000** and **40 units**, what’s my commission?
- Estimate payout for **$300,000** sales and **10 units**.
- What’s my commission on **$150K** with **51 units**? *(includes $1K bonus)*
- Walk me through the tier breakdown for **$200,000** in sales.

### REST

- `GET /` — web form
- `POST /estimate/monthly` — JSON body `{ "sales_amount", "units_sold" }`

### Acceptance examples

| Sales | Units | Tier commission | Unit bonus | Total |
|-------|-------|-----------------|------------|-------|
| $150,000 | 40 | $2,000 | $0 | **$2,000** |
| $150,000 | 51 | $2,000 | $1,000 | **$3,000** |
| $300,000 | 10 | $5,500 | $0 | **$5,500** |

---

## 11. Multi-step & composite queries (agent orchestration)

These require **multiple tools** or reasoning across entities.

| User question | Typical sequence |
|---------------|------------------|
| What did Jordan earn in Q2? (demo narrative) | `get_quota_attainment` → `get_incentive_plan` → `calculate_commission` |
| What did Jordan earn in Q2? (minimal) | `calculate_commission` only |
| Alex thinks payout is wrong | `list_bookings` → `calculate_commission(recompute=true)` → maybe `flag_dispute` |
| Rank all reps by attainment | `list_reps` → N × `get_quota_attainment` → sort |
| Closest to next accelerator | `list_reps` → N × `get_quota_attainment` → band filter |
| West vs East in 2024Q4 | 2 × `get_team_benchmark` |
| How does Priya compare to team? | `get_quota_attainment` + `get_team_benchmark` |
| Plan change impact for AEs | `list_incentive_plans(role=AE)` with different `as_of` |
| Year-over-year for one rep | Multiple `get_quota_attainment` / `calculate_commission` per period |
| All open disputes this quarter | `list_disputes(period=, status=open)` |

See [PLANNING.md](PLANNING.md) for how agent steps map to SQL joins.

---

## 12. Scripted demo prompts (copy-paste)

From `CLAUDE.md` and README — guaranteed to exercise the stack:

1. **What did Jordan earn in Q2 2024?**
2. **Who is closest to their next accelerator this quarter?**
3. **Alex thinks their payout is wrong — help me investigate.**
4. **Rank all reps by attainment in 2024Q4.**
5. **How did the West region stack up vs East in 2024Q4?**
6. **What changed between the 2021 AE plan and the 2024 AE plan?**

Monthly estimator (browser):

7. Open `http://localhost:8080/` — enter **150000** sales, **51** units → **$3,000** total.

---

## 13. Operations & health (non-domain)

| Query / action | REST |
|----------------|------|
| Is the API up? | `GET /healthz` |
| Explore all endpoints | `GET /docs` (Swagger UI) |

---

## 14. Out of scope (not supported)

| Request type | Why |
|--------------|-----|
| Payroll tax, draws, recoveries | Not modeled |
| Login / per-rep security on estimator | Open demo |
| Change another rep’s quota via chat | Read-only ICM except `flag_dispute` create |
| Automatic cross-rep deal crediting fix | No crediting graph in DB |
| Monthly tier rates via MCP | Not in MCP v1.1 |
| Batch leaderboard API | Must fan-out attainment |
| Forecast “what if I close $X next month?” on quarterly ICM | Use monthly estimator or agent math |
| Real CRM / Salesforce live data | Synthetic seed only |
| Periods outside **2021Q1–2025Q4** | Seeder range |
| Spiffs, MBO, clawbacks | Future / BUILD_PLAN Phase 3+ |

---

## 15. Quick reference — MCP tool → question types

| MCP tool | Answers questions about… |
|----------|---------------------------|
| `list_reps` | Who is in the org; filter by role/region |
| `get_quota_attainment` | Quota, bookings, attainment %, deal count for one rep/quarter |
| `get_incentive_plan` | One rep’s active plan (rates, accelerators, OTE) |
| `list_incentive_plans` | Plan catalog and historical comparison |
| `calculate_commission` | Quarterly payout breakdown and explanation |
| `list_bookings` | Individual deals (disputes, evidence) |
| `flag_dispute` | Create payout dispute ticket |
| `list_disputes` | Search dispute history |
| `get_team_benchmark` | Team median, top decile, top/bottom performer |

---

## Related docs

- [REQUIREMENTS.md](REQUIREMENTS.md) — formal requirements
- [PRODUCT_SPEC.md](PRODUCT_SPEC.md) — product specification
- [BUILD_PLAN.md](BUILD_PLAN.md) — delivery phases (e.g. MCP monthly estimator in Phase 2)
- [PLANNING.md](PLANNING.md) — agent planning vs database joins
- [README.md](../README.md) — setup and runbook
- [CLAUDE.md](../CLAUDE.md) — agent skill / behavior rules
