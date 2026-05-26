# Build plan — Sales Incentive Co-work Demo

Phased plan for delivering and extending the product.  
**Legend:** ✅ Done · 🔄 In progress · ⬜ Planned

---

## Phase 0 — Foundation (✅ complete)

**Goal:** Runnable ICM backend + agent demo for developers.

| # | Work item | Deliverable | Status |
|---|-----------|-------------|--------|
| 0.1 | Postgres + Docker Compose | `docker-compose.yml` | ✅ |
| 0.2 | SQLAlchemy models & seeder | `api/app/models.py`, `seed.py` | ✅ |
| 0.3 | Quarterly commission logic | `api/app/logic.py` | ✅ |
| 0.4 | REST API surface | `api/app/main.py` | ✅ |
| 0.5 | MCP wrapper (9 tools) | `mcp_server/icm_mcp.py` | ✅ |
| 0.6 | Agent skill | `CLAUDE.md` | ✅ |
| 0.7 | Public README + cross-platform runbook | `README.md` | ✅ |
| 0.8 | Planning / architecture notes | `docs/PLANNING.md` | ✅ |

**Exit criteria:** `docker compose up` → healthz OK → MCP tools return real data.

---

## Phase 1 — Monthly commission estimator (✅ this release)

**Goal:** Rep-facing web app with marginal tier table + unit bonus; API + docs.

### 1.1 Requirements & design

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1.1.1 | Capture tier table + marginal rule + unit bonus | Docs | ✅ `docs/REQUIREMENTS.md` |
| 1.1.2 | Product spec (ICM + estimator) | Docs | ✅ `docs/PRODUCT_SPEC.md` |
| 1.1.3 | Build plan (this file) | Docs | ✅ |

### 1.2 Backend

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1.2.1 | Pure tier calculator + unit bonus | `api/app/estimator.py` | ✅ |
| 1.2.2 | Pydantic request/response schemas | `api/app/schemas.py` | ✅ |
| 1.2.3 | `POST /estimate/monthly` | `api/app/main.py` | ✅ |
| 1.2.4 | Unit tests for acceptance examples | `api/tests/test_estimator.py` | ✅ |

**Acceptance tests (automated):**

- $150K sales, 40 units → $2,000 commission, $0 bonus, $2,000 total  
- $150K sales, 51 units → $2,000 + $1,000 = $3,000 total  
- $300K sales, 10 units → $5,500 commission  

### 1.3 Frontend

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1.3.1 | Static estimator page | `api/app/static/index.html` | ✅ |
| 1.3.2 | Styles + results table | `api/app/static/styles.css` | ✅ |
| 1.3.3 | Mount static + root route | `api/app/main.py` | ✅ |

### 1.4 Integration & docs

| # | Task | Status |
|---|------|--------|
| 1.4.1 | README: estimator section + link to spec | ✅ |
| 1.4.2 | Dockerfile copies `static/` | ✅ |
| 1.4.3 | Optional: MCP tool `estimate_monthly_commission` | ⬜ (nice-to-have) |

**Exit criteria:** Browser at `http://localhost:8080/` matches API for all cases in REQUIREMENTS §6.

---

## Phase 2 — Agent awareness of estimator (⬜ optional)

**Goal:** Claude can call the monthly estimator via MCP (showcases “add a tool” story).

| # | Task | Effort |
|---|------|--------|
| 2.1 | Add `estimate_monthly_commission` to `icm_mcp.py` | S |
| 2.2 | Extend `CLAUDE.md` with when to use monthly vs quarterly | S |
| 2.3 | Demo prompt: *"If I sell 200K and 60 units this month, what do I earn?"* | S |

---

## Phase 3 — ICM product hardening (⬜ future)

| # | Feature | Notes |
|---|---------|-------|
| 3.1 | `GET /leaderboard?period=` | Removes N+1 agent fan-out |
| 3.2 | Auth (API key or OAuth) | For non-local demos |
| 3.3 | Persist estimator history | Optional audit per rep |
| 3.4 | Align estimator tiers with role-based plans | Bridge monthly vs quarterly |
| 3.5 | GitHub Actions: test + lint on PR | CI |

---

## Phase 4 — UI polish (⬜ future)

| # | Feature |
|---|---------|
| 4.1 | Link estimator to logged-in rep profile |
| 4.2 | Chart: sales vs commission curve |
| 4.3 | Mobile-responsive layout |
| 4.4 | Export PDF estimate |

---

## Implementation order (Phase 1 detail)

Recommended sequence for implementers (already executed in repo):

```
1. estimator.py          ← rate table + marginal math + bonus
2. schemas.py            ← MonthlyEstimateIn / Out
3. test_estimator.py     ← lock acceptance examples
4. main.py               ← POST route + StaticFiles
5. static/*              ← form + fetch + render breakdown
6. docs/*                ← REQUIREMENTS, PRODUCT_SPEC, BUILD_PLAN
7. README                ← discoverability
```

**Estimated effort:** ~2–4 hours for an engineer familiar with FastAPI; ~30 minutes to change rates after Phase 1 ships.

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Confusion between monthly tiers and quarterly ICM | Clear labels in UI; separate API path `/estimate/monthly` |
| Tier boundary off-by-one | Document brackets; unit tests at $100K, $250K boundaries |
| Static files not in Docker image | COPY `app/static` in Dockerfile; smoke test `/` |

---

## Definition of done (release v1.1)

- [x] All Phase 1 tasks  
- [x] `pytest` passes in `api/tests/`  
- [x] Manual: three acceptance scenarios in REQUIREMENTS.md  
- [x] Docs linked from README  
- [x] Committed and pushed to `main`
