# Build plan — from scratch to full demo

Use this document to **build the entire Sales Incentive Co-work demo from an empty folder**,
then run the live demo (Docker → API → web estimator → MCP → Claude).

**Companion docs:** [REQUIREMENTS.md](REQUIREMENTS.md) · [PRODUCT_SPEC.md](PRODUCT_SPEC.md) ·
[query_readme.md](query_readme.md) · [PLANNING.md](PLANNING.md)

**Already built?** Clone `https://github.com/ljohri/sales-incentive-demo` and jump to
[§12 Final verification](#12-final-verification--demo-script).

---

## At a glance

| Phase | What you build | Time (solo) | Demo “chapter” |
|-------|----------------|-------------|----------------|
| A | Repo + Docker + Postgres | 30 min | “Here’s our data layer” |
| B | SQLAlchemy models + seeder | 60–90 min | “Synthetic 5-year sales org” |
| C | Quarterly ICM API + logic | 60–90 min | “Real ICM endpoints” |
| D | MCP server (9 tools) | 30 min | “Wrap REST as agent tools” |
| E | `CLAUDE.md` + Claude wiring | 20 min | “Co-worker agent” |
| F | Monthly estimator UI + API | 45–60 min | “Ship a change in minutes” |
| G | Docs + README | 30 min | “Handoff” |
| **Total** | | **~5–7 hours** | **~90 min live demo** (abbreviated) |

---

## What you are building

```
┌─────────────┐     REST      ┌──────────────┐    MCP/stdio    ┌─────────┐
│ Postgres 16 │ ◄───────────► │ FastAPI :8080│ ◄─────────────► │ Claude  │
└─────────────┘               │  + static UI │                 └─────────┘
                              └──────────────┘
                                     ▲
                              CLAUDE.md (skill)
```

**Deliverables:**

1. **ICM backend** — 20 reps, quarterly quotas/bookings/commissions/disputes, `2021Q1`–`2025Q4`
2. **REST API** — 12+ routes (reps, plans, quota, commission, disputes, benchmark, estimate)
3. **MCP server** — 9 tools for Claude Desktop / Code / Cursor
4. **Monthly estimator** — marginal tier web app at `/`
5. **Documentation** — README, specs, query catalog

---

## Final repository layout

Create this tree by the end of the build:

```
sales-incentive-demo/
├── docker-compose.yml
├── CLAUDE.md
├── README.md
├── LICENSE
├── .gitignore
├── api/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── logic.py          # quarterly commission math
│   │   ├── estimator.py      # monthly marginal tiers + unit bonus
│   │   ├── seed.py
│   │   ├── main.py
│   │   └── static/
│   │       ├── index.html
│   │       ├── styles.css
│   │       └── app.js
│   └── tests/
│       ├── __init__.py
│       └── test_estimator.py
├── mcp_server/
│   ├── requirements.txt
│   └── icm_mcp.py
└── docs/
    ├── REQUIREMENTS.md
    ├── PRODUCT_SPEC.md
    ├── BUILD_PLAN.md         # this file
    ├── PLANNING.md
    ├── query_readme.md
    └── images/
        └── claude-cowork-mockup.png
```

---

## Prerequisites (before you start)

| Tool | Version | Check |
|------|---------|--------|
| Docker Desktop | v4+ with Compose v2 | `docker compose version` |
| Python | 3.10+ (3.12 in Docker) | `python3 --version` |
| Git | any | `git --version` |
| Claude client (for demo finale) | Desktop, Code, or Cursor | optional until §11 |
| Editor | VS Code / Cursor | — |

**Ports must be free:** `5544` (Postgres), `8080` (API).

**Skills:** Basic Python, REST, Docker. No prior MCP experience required.

---

## §1 — Bootstrap the repository

### 1.1 Create project root

```bash
mkdir sales-incentive-demo && cd sales-incentive-demo
git init -b main
```

### 1.2 Add `.gitignore`

Ignore Python artifacts and local venvs (use GitHub’s Python template or minimal):

```
__pycache__/
*.pyc
.venv/
mcp_server/.venv/
api/.venv/
.env
.DS_Store
```

### 1.3 Add `LICENSE`

MIT license (see repo `LICENSE`).

**Gate:** `git status` shows clean untracked files only.

---

## §2 — Docker Compose + Postgres

### 2.1 Create `docker-compose.yml`

Two services:

- **`db`**: `postgres:16-alpine`, user/db/password `icm`, host port **5544** → 5432, named volume `icm-pgdata`, healthcheck `pg_isready`.
- **`api`**: build `./api`, depends on healthy `db`, env `DATABASE_URL=postgresql+psycopg://icm:icm@db:5432/icm`, port **8080**, command runs seeder then uvicorn:

```yaml
command: >
  sh -c "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8080"
```

### 2.2 Create API folder skeleton

```bash
mkdir -p api/app api/tests
touch api/app/__init__.py api/tests/__init__.py
```

### 2.3 Create `api/requirements.txt`

```
fastapi==0.115.5
uvicorn[standard]==0.32.0
SQLAlchemy==2.0.36
psycopg[binary]==3.2.3
pydantic==2.9.2
python-dateutil==2.9.0.post0
pytest==8.3.3
```

### 2.4 Create `api/Dockerfile`

- Base `python:3.12-slim`
- Install `curl` (for HEALTHCHECK)
- `WORKDIR /srv`
- `COPY requirements.txt` → `pip install`
- `COPY app ./app`
- `EXPOSE 8080`
- `HEALTHCHECK` → `curl http://localhost:8080/healthz`
- Default `CMD` uvicorn (overridden by compose to seed first)

### 2.5 Create `api/.dockerignore`

Exclude `__pycache__`, `.venv`, `.git`.

**Gate:** Files exist; compose file validates (`docker compose config`).

---

## §3 — Database layer (`db.py` + `models.py`)

### 3.1 `api/app/db.py`

- Read `DATABASE_URL` from env (default local `postgresql+psycopg://icm:icm@localhost:5544/icm`).
- `create_engine`, `sessionmaker`, `declarative_base`.
- `get_db()` generator for FastAPI `Depends`.

### 3.2 `api/app/models.py` — tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `reps` | Sales org | `employee_id`, name, email, `role` (SDR/AE/EAE), `region`, `territory`, `hire_date` |
| `incentive_plans` | Role plans | `role`, `plan_name`, `effective_start/end`, salary, `commission_rate`, `accelerator_100/120`, `kicker_new_logo` |
| `quotas` | Quarterly quota | `rep_id`, `period` (e.g. `2024Q2`), `quota_amount` |
| `bookings` | Deals | `rep_id`, `deal_id`, `account`, `amount`, `period`, `is_new_logo` |
| `commissions` | Payout snapshot | `rep_id`, `period`, breakdown fields, `plan_id` FK |
| `disputes` | Tickets | `ticket_id`, `rep_id`, `period`, `category`, `status`, amounts |

Use SQLAlchemy `relationship()` from `Rep` to children.

**Gate:** `from app.models import Rep` imports inside container (after §6).

---

## §4 — Quarterly commission logic (`logic.py`)

### 4.1 Implement `compute_commission(...)`

Pure function — no DB. Inputs: `bookings_total`, `quota_amount`, plan rates.

**Buckets:**

```
under_100   = min(bookings, quota)
in_100_120  = max(0, min(bookings, quota * 1.20) - quota)
over_120    = max(0, bookings - quota * 1.20)

base   = under_100  * commission_rate
accel  = in_100_120 * rate * accelerator_100 + over_120 * rate * accelerator_120
kicker = new_logo_bookings * kicker_new_logo_rate
total  = base + accel + kicker
```

Return dataclass with `explanation: list[str]` (human-readable lines).

### 4.2 Helpers

- `quarter_for_date(d)` → `"2024Q2"`
- `median`, `percentile` for team benchmarks

**Gate:** Quick Python REPL test — quota 1M, bookings 1.35M, rate 0.09, accels 1.5/2.0 → non-zero accel lines.

---

## §5 — Data seeder (`seed.py`)

### 5.1 Behavior

- `Base.metadata.create_all(engine)` on run.
- If reps exist and `RESEED!=true` → print skip and exit.
- If `RESEED=true` → drop/create all tables.

### 5.2 `build_plans()`

Six plans: SDR/AE/EAE × (2021–2023, 2024+). See [PRODUCT_SPEC.md](PRODUCT_SPEC.md) §6 for rates.

### 5.3 `build_reps()`

- 20 reps: ~6 SDR, ~10 AE, ~4 EAE.
- Random names from fixed pools; regions West/Central/East/South; territories per region.
- `employee_id` = `E1000` … `E1019`.

### 5.4 `simulate_history()`

For each quarter `2021Q1` … `2025Q4`:

- Per rep (skip if hired after quarter end): insert `Quota`, generate 1–10 `Booking` rows summing to target attainment, compute `Commission` via `logic.compute_commission`, occasionally insert `Dispute`.

Use fixed `RANDOM_SEED=42` for reproducible demos.

### 5.5 Entry point

```python
if __name__ == "__main__":
    main()
```

**Gate (after §6):** `docker compose up --build` logs `[seed] Done.` and ~20 reps.

---

## §6 — Pydantic schemas (`schemas.py`)

Define response models:

- `RepOut`, `IncentivePlanOut`, `QuotaAttainment`, `CommissionBreakdown`
- `DisputeIn`, `DisputeOut`, `TeamBenchmark`
- Later (§9): `MonthlyEstimateIn`, `MonthlyEstimateOut`, `MonthlyTierLine`

Use `model_config = ConfigDict(from_attributes=True)` where reading ORM objects.

---

## §7 — REST API (`main.py`)

### 7.1 App setup

```python
app = FastAPI(title="ICM Demo API", version="1.0.0")
Base.metadata.create_all(engine)
```

### 7.2 Helper `_resolve_rep(db, rep: str)`

Match in order:

1. `employee_id` (case-insensitive)
2. `email`
3. `"First Last"` (first + last)
4. First name only → if multiple matches, **HTTP 409** with candidate list

### 7.3 Endpoints to implement (in order)

| # | Method | Path | Notes |
|---|--------|------|-------|
| 1 | GET | `/healthz` | `{"status":"ok"}` |
| 2 | GET | `/reps` | Optional `role`, `region` query params |
| 3 | GET | `/reps/{rep}` | Single rep |
| 4 | GET | `/incentive-plans` | Optional `role`, `as_of` date |
| 5 | GET | `/incentive-plans/for-rep/{rep}` | Plan for rep’s role on `as_of` (default today) |
| 6 | GET | `/quota-attainment` | Query `rep`, `period`; sum bookings |
| 7 | GET | `/commission` | Query `rep`, `period`, `recompute` bool |
| 8 | POST | `/disputes` | Body `DisputeIn`; generate `DISP-#####` |
| 9 | GET | `/disputes` | Filter `rep`, `period`, `status` |
| 10 | GET | `/team-benchmark` | Join `Commission` ⋈ `Rep`; median, top decile, top/bottom names |
| 11 | GET | `/bookings` | Query `rep`, optional `period` |

**Commission endpoint details:**

- Resolve plan by `rep.role` + quarter start date (not “today”).
- Default: return stored `Commission` row + rebuild `explanation` via `logic.compute_commission`.
- `recompute=true`: load all `Booking` for period, sum amounts and new-logo, call `compute_commission`.

### 7.4 Implement incrementally

Build 1–3 endpoints → bring Docker up → curl test → add next group.

**Gate — backend ICM:**

```bash
docker compose up --build -d
curl -s http://localhost:8080/healthz
curl -s 'http://localhost:8080/reps' | head -c 400
curl -s 'http://localhost:8080/quota-attainment?rep=Priya&period=2024Q2'
curl -s 'http://localhost:8080/commission?rep=E1002&period=2025Q1'
curl -s 'http://localhost:8080/team-benchmark?period=2024Q4&role=AE'
```

Open `http://localhost:8080/docs` — all routes listed.

---

## §8 — MCP server (`mcp_server/`)

### 8.1 `mcp_server/requirements.txt`

```
mcp[cli]>=1.2.0
httpx>=0.27.0
```

### 8.2 `mcp_server/icm_mcp.py`

- `FastMCP("icm-demo")`
- `API_URL = os.environ.get("ICM_API_URL", "http://localhost:8080")`
- Helpers `_get`, `_post` with `httpx`

**Nine `@mcp.tool()` functions** — thin wrappers:

| Tool | HTTP |
|------|------|
| `list_reps` | GET `/reps` |
| `get_quota_attainment` | GET `/quota-attainment` |
| `get_incentive_plan` | GET `/incentive-plans/for-rep/{rep}` |
| `list_incentive_plans` | GET `/incentive-plans` |
| `calculate_commission` | GET `/commission` |
| `list_bookings` | GET `/bookings` |
| `flag_dispute` | POST `/disputes` |
| `list_disputes` | GET `/disputes` |
| `get_team_benchmark` | GET `/team-benchmark` |

`if __name__ == "__main__": mcp.run()` (stdio).

### 8.3 Local install

```bash
cd mcp_server
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Gate:**

```bash
ICM_API_URL=http://localhost:8080 python icm_mcp.py
# waits on stdin — Ctrl+C to exit
```

List tools from Claude after §11, or run a one-liner test importing `icm_mcp` and calling `get_quota_attainment` via MCP SDK if you have it.

---

## §9 — Agent skill (`CLAUDE.md`)

Create repo-root `CLAUDE.md` with:

1. **Role** — Sales Incentive Co-worker agent.
2. **Tool table** — all 9 MCP tools and when to use each.
3. **Domain primer** — periods `YYYYQn`, roles, regions, plan structure, **commission formula** (copy from §4).
4. **Behavior rules** — tool-first, show reasoning chain, fan-out OK, dispute workflow, currency formatting.
5. **Demo prompts** — Jordan Q2, Alex dispute, accelerator proximity, rank reps, West vs East.
6. **Hard rules** — no fabricated numbers, surface 409, no dispute without investigation.

Claude Code loads this automatically when working in the repo.

**Gate:** File committed; readable by humans in the room.

---

## §10 — Monthly commission estimator (Phase F)

*Demo narrative: “Now we add a rep-facing feature in under an hour.”*

### 10.1 `api/app/estimator.py`

- `BRACKETS` list: `(cap, rate, label)` — caps at 100K, 250K, then `None` for remainder.
- `compute_monthly_commission(sales_amount, units_sold)`:
  - Marginal loop over brackets
  - `unit_bonus = 1000 if units_sold > 50 else 0`
  - Return dataclass + `explanation` lines

### 10.2 Schemas

`MonthlyEstimateIn` (`sales_amount >= 0`, `units_sold >= 0`), `MonthlyEstimateOut`, `MonthlyTierLine`.

### 10.3 Routes in `main.py`

```python
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def estimator_page(): return FileResponse(STATIC_DIR / "index.html")

@app.post("/estimate/monthly", response_model=MonthlyEstimateOut)
def estimate_monthly_commission(payload: MonthlyEstimateIn): ...
```

### 10.4 Static UI (`api/app/static/`)

| File | Responsibility |
|------|----------------|
| `index.html` | Form: sales $, units; rate table; results table |
| `styles.css` | Dark theme, readable tables |
| `app.js` | `POST /estimate/monthly` on submit; render tier lines + total |

### 10.5 Tests `api/tests/test_estimator.py`

Assert:

- 150K / 40 units → $2,000 total
- 150K / 51 units → $3,000 total
- 300K / 10 units → $5,500 tiered

Run:

```bash
cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/pytest tests/ -q
```

### 10.6 Rebuild Docker

```bash
docker compose up --build -d api
```

**Gate:**

- `http://localhost:8080/` loads UI
- 150000 + 51 units → **$3,000** total
- `curl -X POST http://localhost:8080/estimate/monthly -H 'Content-Type: application/json' -d '{"sales_amount":150000,"units_sold":51}'`

**Live demo tweak:** Change `BRACKETS` rates in `estimator.py`, rebuild — show audience one-file change.

---

## §11 — Wire Claude (MCP config)

### 11.1 Claude Desktop (`claude_desktop_config.json`)

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "icm-demo": {
      "command": "/ABSOLUTE/PATH/sales-incentive-demo/mcp_server/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/sales-incentive-demo/mcp_server/icm_mcp.py"],
      "env": { "ICM_API_URL": "http://localhost:8080" }
    }
  }
}
```

Windows: use `Scripts/python.exe` and forward slashes in JSON paths.

**Restart Claude completely** after editing.

### 11.2 Claude Code

```bash
cd sales-incentive-demo
export ICM_API_URL=http://localhost:8080
claude mcp add icm-demo --scope project -- \
  "$(pwd)/mcp_server/.venv/bin/python" "$(pwd)/mcp_server/icm_mcp.py"
```

### 11.3 Cursor

`.cursor/mcp.json` — same JSON shape as Desktop.

**Gate:** New chat shows **icm-demo** tools; ask *"List all AEs"* → returns JSON from API.

---

## §12 — Documentation package

Create under `docs/` (can copy from this repo):

| File | Contents |
|------|----------|
| `REQUIREMENTS.md` | R1–R7, NFRs, acceptance criteria |
| `PRODUCT_SPEC.md` | Full spec ICM + estimator |
| `PLANNING.md` | Agent vs SQL joins |
| `query_readme.md` | All supported natural-language queries |
| `BUILD_PLAN.md` | This file |

Expand root `README.md`:

- Prerequisites, 3-step quick start (Docker → MCP venv → Claude config)
- Link to product docs and query catalog
- API table including `/` and `/estimate/monthly`
- Demo prompts

Optional: `docs/images/claude-cowork-mockup.png` for README hero.

**Gate:** New teammate can follow README only and reach working stack.

---

## §13 — Final verification & demo script

### 13.1 Automated checks

```bash
docker compose ps          # db + api healthy
curl -s http://localhost:8080/healthz
cd api && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

### 13.2 ICM API spot checks

```bash
curl -s 'http://localhost:8080/quota-attainment?rep=Jordan&period=2024Q2'
curl -s 'http://localhost:8080/commission?rep=Priya&period=2025Q1'
curl -s 'http://localhost:8080/team-benchmark?period=2024Q4&region=West'
```

### 13.3 Estimator spot checks

| Sales | Units | Expected total |
|-------|-------|----------------|
| 150,000 | 40 | $2,000 |
| 150,000 | 51 | $3,000 |
| 300,000 | 10 | $5,500 |

### 13.4 Agent spot checks (Claude + MCP)

Run these prompts in order for a **90-minute live build demo** (abbreviated if repo pre-exists):

| Min | Audience sees | You do / say |
|-----|---------------|--------------|
| 0–10 | Empty folder → `docker compose` | §1–2, show Postgres healthy |
| 10–25 | Models + seed | §3–5, `docker compose` logs `[seed] Done` |
| 25–45 | Swagger `/docs` | §6–7, curl quota + commission |
| 45–55 | MCP tools appear in Claude | §8–11, `list_reps` in chat |
| 55–65 | *"What did Jordan earn in Q2 2024?"* | Tool chain + explanation |
| 65–75 | Browser estimator | §10, 150K / 51 units = $3K |
| 75–85 | Edit `estimator.py` rate | Rebuild → new total (easy change story) |
| 85–90 | *"Rank reps in 2024Q4"* / dispute prompt | Fan-out + `flag_dispute` optional |

Full prompt list: [query_readme.md](query_readme.md) §12.

### 13.5 Publish (optional)

```bash
git remote add origin git@github.com:<you>/sales-incentive-demo.git
git add -A && git commit -m "Initial ICM co-work demo"
git push -u origin main
```

---

## §14 — Troubleshooting during the build

| Symptom | Fix |
|---------|-----|
| `port is already allocated` | Change host ports in `docker-compose.yml` |
| API restart loop | `docker compose logs api`; often DB not ready — check healthcheck |
| Seeder runs every start but skips data | Expected: "reps already exist"; use `RESEED=true` once |
| Claude has no tools | Absolute paths in MCP config; restart app; `ICM_API_URL` set |
| MCP connection refused | API must be on host `localhost:8080` from Claude’s perspective |
| Estimator 404 | Ensure `static/` copied in Docker image; `GET /` route registered |
| 409 on rep name | Use full name or `employee_id` |
| Plan wrong for old quarter | Pass `as_of=YYYY-MM-DD` on plan endpoint |

---

## §15 — Roadmap after v1.1 (not required for scratch build)

| Phase | Goal | Key tasks |
|-------|------|-----------|
| **2** | MCP monthly estimator | `estimate_monthly_commission` tool + `CLAUDE.md` |
| **3** | Hardening | `GET /leaderboard`, auth, CI |
| **4** | UI polish | Charts, mobile, PDF export |

See tables in git history for status legend (✅ / ⬜).

---

## §16 — Definition of done (full project)

- [ ] `docker compose up --build` succeeds from clean clone
- [ ] 20 reps seeded; quarters 2021Q1–2025Q4 queryable
- [ ] All §7 REST endpoints respond (see `/docs`)
- [ ] 9 MCP tools callable with API running
- [ ] `CLAUDE.md` present; agent answers scripted prompts without inventing data
- [ ] Estimator UI + `POST /estimate/monthly` pass acceptance table (§13.3)
- [ ] `pytest` passes
- [ ] README + docs/ complete

When all boxes are checked, the project matches the public reference implementation on GitHub.
