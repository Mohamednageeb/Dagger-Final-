[English](#english) · [العربية](#العربية)

# Daggers — One Brain, All Surfaces

**Catch scams, prove them with evidence, report them, and block them on every device.**

> ⚠️ **Status: independent hackathon / research prototype.** Daggers was built for the
> **SCAMSHIELD AI Hackathon** (Abu Dhabi Police × 42 Abu Dhabi). It is **not** an official product of
> Abu Dhabi Police, UAE Police or any UAE Government entity, is not endorsed or operated by them, and
> has no access to police or government systems. Do not present it as official without written
> authorisation.
>
> ⚠️ **حالة المشروع: نموذج أولي مستقل للهاكاثون والبحث.** بُني Daggers لـ **هاكاثون SCAMSHIELD AI**
> (شرطة أبوظبي × 42 أبوظبي). وهو **ليس** منتجاً رسمياً لشرطة أبوظبي أو شرطة الإمارات أو أي جهة حكومية
> إماراتية، ولا تعتمده هذه الجهات ولا تشغّله، ولا يتصل بأي نظام شرطي أو حكومي. لا تقدّمه على أنه رسمي
> دون تفويض مكتوب.

---

# English

## Contents

1. [Run it (4 steps)](#run-it-4-steps)
2. [Project overview — the complete system](#1-project-overview--the-complete-system)
3. [Speed and performance](#2-speed-and-performance)
4. [How everything integrates](#3-how-everything-integrates)
5. [Configuration, tests and deployment](#4-configuration-tests-and-deployment)
6. [Debugging and troubleshooting playbook](#5-debugging-and-troubleshooting-playbook)
7. [Honest limitations, security boundaries and roadmap](#6-honest-limitations-security-boundaries-and-roadmap)
8. [Documentation map](#7-documentation-map)

## Run it (4 steps)

**Prerequisites:** Linux or macOS, `make`, **Python 3.11+**, internet access for the first install.
Node.js and Google Chrome are needed only for the extension and the browser tests.

```bash
# 1. go to the project folder inside the repository / unzipped download
cd daggers-main            # the folder that contains Makefile, backend/, web/

# 2. create .venv and install the pinned dependencies (public PyPI, even behind a private mirror)
make bootstrap PIP_INDEX=https://pypi.org/simple

# 3. approve the verified official / organisation entries ON THIS MACHINE, download the
#    worldwide ranking list, clear stored Checker results and run the self-check
make setup-trust

# 4. start the server with the Guard's DNS-over-HTTPS resolver switched on
GUARD_DOH_ENABLED=1 make dev
```

Then open (no sign-in — see [Open access](#open-access-no-sign-in)):

| Page | Address |
|---|---|
| Checker | http://localhost:8000/#/check |
| Number check | http://localhost:8000/#/number |
| Police Portal (all findings, reports, AI) | http://localhost:8000/#/portal |
| The Guard (live block list, stats, test bar) | http://localhost:8000/#/guard |
| Radar feed | http://localhost:8000/#/feed |
| Sweep (search / maps) | http://localhost:8000/#/sweep |
| Verdict page | http://localhost:8000/verdict?domain=example.com |
| DNS-over-HTTPS | http://localhost:8000/dns-query (step 4 enables it) |

Quick check: in the Checker, check `https://dubaipolice-fines-pay.top/login` → **FAKE**; it appears
in the Portal and in the Guard's "Newest fakes" within seconds. Stop the server with **Ctrl+C**.

Notes:
* "Address already in use" → an old server is running: `pkill -f "uvicorn backend.app.main"`, or
  `make dev PORT=8001`.
* Run `make setup-trust` again after every pull, and **do not commit**
  `backend/app/channels/official/registry.yaml` after approving (approvals are per installation).
* `make dev` reads `.env` automatically if it exists (`cp .env.example .env`).

### Open access (no sign-in)

`make dev` sets `OPEN_ACCESS=1`: **every visitor, on any device, uses the Police Portal as the admin
user `local` without a password** (team decision for the demo). Changes still need the same-origin
CSRF token and are audited. Anyone who can reach the site can read and change portal data — use it
only on non-sensitive data. To require accounts: `make dev OPEN_ACCESS=0`, then
`make user U=alice R=investigator` (roles `viewer` < `investigator` < `admin`) and sign in at `#/login`.

---

## 1. Project overview — the complete system

Daggers is one FastAPI process (`backend/app/main.py`) that serves the API **and** the bilingual web
app on the same origin, with SQLite (WAL) as its database. Every surface — Checker, Radar, Sweep,
Police Portal, Chrome extension, Guard — gets its verdict from **one brain** through **one central
trust policy**. There is **one runtime mode: live** — no demo mode, no seed data, no fixture fallback;
a fresh install is empty.

### Verdicts

| Final `tag` (what every client shows) | Meaning |
|---|---|
| **SAFE** | only via an approved path: an approved, fresh official-registry domain (class A/B), an approved news outlet (C) or verified organisation (P), a widely used site from the Tranco top list (`REPUTATION_TOP_N`, default 60,000), or an established site (registered ≥ 730 days by RDAP, HTTPS, no warning signs) — always with nothing suspicious |
| **WARNING** | unknown, unverified, unavailable, or suspicious but not confirmed. **Unknown never becomes SAFE.** |
| **MISLEADING** | a government/organisation claim contradicted by, or not verifiable against, approved sources; unverifiable offers |
| **FAKE** | sufficiently supported fraud, phishing or impersonation |

The engine verdict (`verdict`: `MALICIOUS / MISLEADING / SUSPICIOUS / UNKNOWN`) is kept for
compatibility; `tag` is authoritative. Policy `daggers-trust-2.2`, engine `daggers-engine-3.1`.

### The eight parts

| # | Part | Where | What it does (implemented) |
|---|---|---|---|
| 1 | **Core brain** | `backend/app/core/`, `backend/app/channels/{scoring,trust_policy,reputation,established}.py`, `backend/app/channels/official/`, `backend/app/intel/` | Deterministic scorer (`scorer.py`): URL/IDN normalisation, lexical and identity signals, brand look-alikes, **homograph / confusable** detection (`homograph.py`, data in `rules.yaml`), bilingual EN/AR/Arabizi **claim and lure** analysis (`claims.py`, `lures.yaml`), message analysis (`message.py`: OTP/card requests, payment demands, delivery lures, urgency, impersonation), phone-number rules (`numbers.py`, used by the **Number check** and Maps listings). Official UAE source **registry** (`registry.yaml`, CLI) and **claim verification** against approved records (`official/verify.py`, `compare.py`). Live evidence for the Checker: RDAP domain age, Certificate Transparency, read-only page probe, threat feeds (`intel/`). Central policy `trust_policy.decide()` with reason codes. |
| 2 | **Radar & Vision** | `backend/app/radar/`, `backend/app/vision/` | Certificate Transparency polling via crt.sh (`crt.py`), threat feeds OpenPhish / URLhaus / PhishTank-with-key (`feeds.py`), RDAP / DNS / TLS / favicon enrichment, each call under its own timeout (`enrich.py`), pipeline (`pipeline.py`). Vision: Playwright screenshots with a hard timeout that aborts every non-GET request and never fills forms (`render.py`), ORB + RANSAC clone similarity when OpenCV is installed, perceptual-hash fallback otherwise (`diff.py`, `gallery.py`), annotated evidence images, optional Tesseract OCR (`ocr.py`). **All off by default** (`CRT_ENABLED`, `FEEDS_ENABLED`, `ENRICH_ENABLED`, `RENDER_ENABLED`); vision packages are optional (`make install-render`). |
| 3 | **Checker** | `POST /api/check`, `backend/app/checker.py`, `web/js/views/check.js` | Paste a **link/domain or a message**. Classifies, normalises, runs the brain + live evidence (`CHECK_EVIDENCE_DEADLINE_S`), removes personal data from messages, **sends** every new result to the Police Portal as a finding (source `checker`) and keeps its **own** result store (`CHECKER_STORE_PATH`, reused for `CHECK_CACHE_TTL_S`). History restores after closing the browser. **Number check** (`#/number`, `POST /api/number`, `web/js/views/number.js`): a phone number that called or texted you is checked with offline rules (premium-rate, call-back/VoIP, repeats, pattern catalogue); never SAFE (no signs = WARNING "not verified"); **nothing stored**. |
| 4 | **Sweep** | `backend/app/channels/{search,maps,sweep}.py`, `POST /api/sweep` | Web search via Serper (key) and DuckDuckGo when `SEARCH_LIVE_ENABLED=1`; Maps via Google Places when `MAPS_LIVE_ENABLED=1` + key. Every result goes through the same brain and policy; FAKE/MISLEADING live results become findings. Runs in the background (202 + polling). No fixtures in the runtime — without a provider a sweep fails honestly. |
| 5 | **The Guard** | `backend/app/guard/`, `backend/app/api/guard.py`, `guard/` | Live DNS blocking of **FAKE domains only**. Checker link checks, Radar, Sweep and investigations feed an O(1) in-memory index persisted in SQLite. Serves hosts / domains / AdGuard lists, an RFC 8484 **DoH resolver** `/dns-query`, a bilingual verdict page `/verdict`, live stats and SSE `guard` events; pushes to a **NextDNS** denylist (key + profile); VPS sidecar for **AdGuard Home** + nginx (`guard/sync.py`, `guard/nginx-verdict.conf`). Never blocks WARNING/UNKNOWN, IPs, government zones, registry, brand-official, shared-platform or widely used domains. |
| 6 | **Chrome extension (MV3)** | `extension/` | Labels **organic** Google results (google.com / google.ae) with the backend `tag` via `POST /api/scan`; skips ads, map packs and carousels; handles dynamic results with a debounced `MutationObserver`. Failure → grey **NOT CHECKED**, never SAFE. Permissions: `storage` + localhost (other backends asked per origin). Collects no browsing history. |
| 7 | **Police Portal, evidence & AI Analyst** | `web/js/views/portal.js`, `backend/app/api/{investigations,reports,ai}.py`, `backend/app/reports/`, `backend/app/ai/` | Searchable index of every finding; investigations; reports with **zero-PII evidence** (validated) and lifecycle `QUEUED → SUBMITTED → SEEN`; auto-filing for high-similarity clones (`AUTOFILE_CLONE_MIN`); export pack; audit log. AI Analyst **Gemini → Groq → deterministic template** for EN/AR case summaries and takedown drafts — it explains stored evidence and **never sets the verdict**. |
| 8 | **Bilingual PWA** | `web/` | Neo-Outline Soft light UI, full EN/AR with RTL (`web/js/i18n/en.json`, `ar.json`, parity enforced), live SSE stream, installable PWA; the service worker caches the app shell and **public** API reads only. |

---

## 2. Speed and performance

### Measured (real run)

`make bench` (`ops/bench.py`) — offline paths only, temporary database, no network. Measured on
2026-11-25 on the build machine (2 CPUs, Python 3.13) on this code:

| Operation | Median | p95 |
|---|---|---|
| Offline scan: brain + central policy (the extension's `/api/scan` path), n = 200 | 4.16 ms | 6.17 ms |
| Guard lookup, 50,000 listed domains, parent-site match | 8.8 µs | 11.3 µs |
| Guard lookup, name not listed | 2.9 µs | 3.9 µs |
| DoH answer for a blocked name (parse + lookup + answer) | 13.3 µs | 19.3 µs |

Your numbers will differ by machine — run `make bench`. No other latency figure is claimed. Live
Checker evidence (RDAP, page, CT) depends on the network and is bounded by
`CHECK_EVIDENCE_DEADLINE_S` (default 10 s).

### Why it is fast (architecture)

* **Deterministic brain, no network on the offline tier.** Rules, lexicon, homographs and claims run in
  memory; `/api/scan` (extension) and Sweep make no per-result outbound calls.
* **O(1) Guard index** (dict + parent-site walk) warmed from SQLite (WAL) at start-up; provider pushes
  are **debounced** (`GUARD_SYNC_DEBOUNCE_S`) into one sync.
* **Timeout isolation.** Radar enrichment wraps RDAP, DNS, TLS and favicon each in
  `asyncio.wait_for`; the Checker's live evidence shares one deadline; rendering has a hard timeout.
  A slow or failing source becomes "unavailable", never a stalled request.
* **Score-gated vision.** Screenshots run only when `RENDER_ENABLED=1` **and** the score is ≥
  `RENDER_SCORE_MIN` (0.45) or the verdict is MISLEADING/MALICIOUS. Reference screenshots are rendered
  on demand into `GALLERY_DIR`; ORB+RANSAC only when OpenCV is present.
* **Server-Sent Events** (`/api/stream`: `finding`, `sweep`, `guard`, `heartbeat`) — no polling.
* **Caches with correct invalidation.** Checker result store (6 h / 10 min partial) keyed by engine,
  policy, registry, reputation and build fingerprint, so any code or data change re-analyses; search
  TTL cache; in-memory RDAP cache; DoH 30-second answer cache; extension-side result cache.

---

## 3. How everything integrates

```
 Browser PWA + Police Portal      Chrome extension (MV3)     Phones / routers / NextDNS / AdGuard Home
        │ same origin                    │ POST /api/scan          │ /dns-query · lists · /verdict
        ▼                                ▼                         ▼
 ┌──────────────── FastAPI app  backend/app/main.py  (Caddy HTTPS in production) ─────────────────┐
 │ routers: auth · system · examples · check · findings · scan · health · stream · investigations │
 │          reports · ai · sweep · guard                                                          │
 │                                                                                                │
 │ Runtime ── ONE verdict path ──────────────────────────────────────────────────────────────┐   │
 │   core/scorer (+claims, message, homograph)  →  channels/scoring.ShieldScorer             │   │
 │   (registry auth · reputation · established site · claim verification · live evidence)    │   │
 │   →  channels/trust_policy.decide  →  tag + reasons + reason_codes + evidence             │   │
 │                                                                                           │   │
 │ radar/ (crt.sh · feeds · enrich) → vision/ (render · diff)        reports/ (queue, zero-PII)│  │
 │ channels/ search · maps · sweep (background)                      ai/ Gemini → Groq → template│ │
 │ guard/ eligibility · O(1) index · manager (debounced sync) · nextdns · doh                  │  │
 │ checker_store/ (own SQLite)          db/repo.py — ALL SQL — SQLite WAL (findings, reports,  │  │
 │                                      sweeps, guard, users, sessions, audit)                │  │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### The five data flows (as wired)

1. **Radar** — crt.sh / feeds → enrichment (timeouts) → brain → optional vision (score-gated) →
   finding in SQLite → SSE `finding` → auto-filed report when the clone score ≥ `AUTOFILE_CLONE_MIN` →
   Guard (FAKE only) with SSE `guard`.
2. **Checker** — `POST /api/check` → classify / normalise → brain + live evidence + official claim
   verification → trust policy → personal data removed → finding sent to the Portal and own store →
   FAKE **link** checks listed on the Guard at once (response carries `guard`). The extension uses
   `POST /api/scan`: same brain and policy, **nothing stored, nothing listed**.
3. **Sweep** — `POST /api/sweep` (202) → background run → Serper/DuckDuckGo or Google Places →
   brain + policy per result → results stored → FAKE/MISLEADING become findings → SSE `sweep` →
   FAKE domains to the Guard.
4. **Report → AI** — `POST /api/reports` builds zero-PII evidence from a finding (validated) →
   `POST /api/report/{id}/analysis` (streams) and `/takedown` built server-side from stored evidence →
   stored on the report → Portal; lifecycle via `/api/reports/{id}/advance`, export pack via `/export`.
5. **Guard** — eligibility (FAKE only, protected domains refused) → O(1) index + `guard_blocklist`
   table → `/api/guard/feed`, `blocklist.txt`, `domains.txt`, `adguard-rules.txt`, `/dns-query`,
   NextDNS push (debounced, cooldown on manual sync), AdGuard Home sidecar → Guard page (SSE) and
   `/verdict`.

### Interface contracts and workstream boundaries

The code references these contracts: **C1** finding shape (`backend/app/db/repo.py`, `backend/app/api/findings.py`; report
evidence = C1 + tag + `evidence_id`), **C4** report lifecycle (`backend/app/reports/queue.py`), **C6** Guard feed
row `{domain, verdict, reason, flagged_at}` (`backend/app/guard/manager.py`). The original workstream spec that
defines C2, C3, C5 and C7 is **not included in this repository**, so they are not documented here.
The full API contract is in [docs/API.md](docs/API.md).

| Workstream | Owns | Status ([docs/INTEGRATION-REPORT.md](docs/INTEGRATION-REPORT.md)) |
|---|---|---|
| WS1 Intelligence Engine | `core/`, `radar/`, `vision/`, `db/`, `main.py` | base of the merge; the `UNKNOWN → SAFE` UI mapping was corrected to `UNKNOWN → WARNING` |
| WS2 Shield & Channels | `channels/` (trust policy, registry, verification, search, maps, sweep), `guard/`, `extension/` | its five WS1 patches (0001–0005) are **applied**; `patches/` removed |
| WS3 Face & Analyst | `web/`, `ai/`, report/AI routes | merged on the WS1 repository; the WS3 stand-in server and in-memory store were removed |

No integration patch is pending in this repository. What still needs **human action**: registry
approval on each installation (`make setup-trust`) and the external accounts listed in §6.

---

## 4. Configuration, tests and deployment

### Prerequisites

| Need | For |
|---|---|
| Python **3.11+**, `make` | everything (`make bootstrap` checks the version) |
| Node.js (tested with 22) | `make test-ext`, `make gates`, browser tests |
| Google Chrome + Playwright | extension, `make e2e*` browser tests |
| Optional: `make install-render` (Playwright Chromium, OpenCV, imagehash, NumPy, pytesseract) | Radar screenshots and clone detection |

### Configuration (`.env`)

`cp .env.example .env` and edit; every switch has a safe default and **no key is required to run**.
Never commit `.env`. Main groups (all names exist in `.env.example`):

| Area | Variables |
|---|---|
| Environment & access | `APP_ENV` (`dev`/`production`), `PORT`, `OPEN_ACCESS`, `LOCAL_OPEN_ACCESS`, `COOKIE_SECURE`, `SESSION_TTL_HOURS`, `LOGIN_MAX_FAILURES`, `SCAN_RATE_PER_MIN`, `TRUST_PROXY_HEADERS`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` |
| Storage | `DB_PATH`, `EVIDENCE_DIR`, `GALLERY_DIR`, `CHECKER_STORE_PATH`, `OFFICIAL_REGISTRY_PATH`, `OFFICIAL_SNAPSHOT_DIR`, `WEB_DIR` |
| Checker | `CHECK_CACHE_TTL_S`, `CHECK_CACHE_PARTIAL_TTL_S`, `CHECK_RDAP_ENABLED`, `CHECK_PAGE_FETCH_ENABLED`, `CHECK_CT_ENABLED`, `CHECK_EVIDENCE_DEADLINE_S`, `CT_API_URL`, `CT_API_KEY` |
| Reputation | `REPUTATION_LIST_PATH`, `REPUTATION_AUTO_UPDATE`, `REPUTATION_TOP_N`, `REPUTATION_MAX_AGE_DAYS` |
| Engine thresholds | `MALICIOUS_THRESHOLD`, `SUSPICIOUS_THRESHOLD`, `RENDER_SCORE_MIN`, `AUTOFILE_CLONE_MIN` |
| Radar | `CRT_ENABLED`, `FEEDS_ENABLED`, `ENRICH_ENABLED`, `RENDER_ENABLED`, `PHISHTANK_KEY`, `HTTP_TIMEOUT_S`, `HTTP_USER_AGENT`, `CRT_MIN_QUERY_GAP_S`, `CRT_POLL_INTERVAL_S`, `FEED_POLL_INTERVAL_S`, `PIPELINE_POLL_INTERVAL_S`, `HEARTBEAT_INTERVAL_S` |
| Sweep | `SEARCH_LIVE_ENABLED`, `SERPER_API_KEY`, `MAPS_LIVE_ENABLED`, `GOOGLE_PLACES_API_KEY`, `SWEEP_ALLOW_ARBITRARY`, `SWEEP_RATE_PER_MIN`, `SWEEP_MAX_CONCURRENT` |
| Guard | `GUARD_ENABLED`, `GUARD_MAX_AGE_DAYS`, `GUARD_INCLUDE_MISLEADING` (legacy alias `GUARD_BLOCK_MISLEADING`), `GUARD_SOURCES`, `GUARD_SYNC_DEBOUNCE_S`, `GUARD_SYNC_COOLDOWN_S`, `GUARD_PUBLIC_ORIGIN`, `GUARD_DOH_ENABLED`, `GUARD_UPSTREAM_DOH`, `GUARD_DOH_BLOCK_MODE`, `GUARD_DOH_RATE_PER_MIN`, `GUARD_VERDICT_IP`, `NEXTDNS_PROFILE_ID`, `NEXTDNS_API_KEY`, `GUARD_DOT_HOSTNAME` |
| AI | `AI_PROVIDER` (`auto`/`gemini`/`groq`/`template`), `AI_ON`, `AI_STATE`, `GEMINI_KEY`, `GROQ_KEY` |
| Docker/Caddy | `DAGGERS_DOMAIN` |

### Official registry (CLI)

Every entry **ships as `pending`**; nothing is SAFE through the registry until it is approved on
your machine.

```bash
make setup-trust                                  # approve all entries whose provenance records a verification (+ ranking list, doctor)
make approve-verified                             # only the approval step
make registry ARGS="list --status pending"        # list / show / validate
make registry ARGS="approve wam"                  # one entry (reviewer name optional: --reviewer "Name")
make registry ARGS="revoke wam"                   # withdraw approval
make registry ARGS="fetch wam"                    # retrieve official records into OFFICIAL_SNAPSHOT_DIR (network)
make trust-status                                 # registry approvals + ranking list status
make reputation-update                            # download the Tranco top-sites list
```

### Chrome extension

`chrome://extensions` → **Developer mode** → **Load unpacked** → select `extension/`. With the
server on `http://localhost:8000`, search on google.com or google.ae. Change the backend URL in the
popup (HTTPS required except localhost). Details: [extension/README.md](extension/README.md).

### Tests

```bash
make check                       # compile + backend tests + extension tests + i18n/syntax gates
make test                        # backend: pytest backend/tests -q
make test-ext                    # extension logic (node --test)
make gates                       # EN/AR key parity, no hardcoded text, JS syntax
make bench                       # offline timing (see §2)
make verify-empty                # a fresh install contains no product data

# targeted
.venv/bin/python -m pytest backend/tests/test_guard_live.py -q          # Guard
.venv/bin/python -m pytest backend/tests/test_gov_safe.py -q            # government SAFE / registry
.venv/bin/python -m pytest backend/tests/test_checker.py -q             # Checker scenarios
.venv/bin/python -m pytest backend/tests/ws2 -q                         # WS2 trust policy, channels
.venv/bin/python -m pytest backend/tests/ws3 -q                         # WS3 AI
```

Browser tests (real Chrome against a running server; `make dev` in another terminal):
`make e2e PORTAL_USER=… PORTAL_PASS=…` (start with `OPEN_ACCESS=0` and create the user first),
`make e2e-guard`, `make e2e-gov …`, `make e2e-rep …`, `make e2e-restore PHASE=1|2` — see the comments
in the `Makefile`.

**Last run on this code (2026-11-25):** backend **454 passed**, extension **10/10**, gates clean,
`make e2e` **35/35**, `make e2e-guard` **19/19**. Earlier runs and gaps:
[docs/TESTING-REPORT.md](docs/TESTING-REPORT.md).

### Deployment

* **Implemented: Docker Compose + Caddy HTTPS** (`Dockerfile`, `docker-compose.yml`,
  `deploy/Caddyfile`). Set `DAGGERS_DOMAIN` and `CORS_ORIGINS` in `.env`, then
  `docker compose up -d --build`. Data lives in the `daggers-data` volume. Full steps, backups and
  rollback: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The image has **not** been built in our test
  environment.
* **Guard, Path A (no VPS):** any HTTPS host for Daggers + NextDNS (`NEXTDNS_PROFILE_ID`,
  `NEXTDNS_API_KEY`) + optional DoH. **Path B (VPS):** AdGuard Home + nginx verdict server
  (`guard/AdGuardHome.yaml.example`, `guard/nginx-verdict.conf`, `make guard-sync`). See
  [guard/README.md](guard/README.md).
* **Static web elsewhere:** `web/config.js` sets `window.API_BASE`. The repository contains **no**
  ready-made configuration for Hugging Face Spaces, Render or Cloudflare Pages.
* **Phone demo without hosting:** a temporary HTTPS tunnel, e.g.
  `cloudflared tunnel --url http://localhost:8000`, then use `https://<tunnel>/dns-query` as Chrome's
  custom secure DNS on Android (start with `GUARD_PUBLIC_ORIGIN=https://<tunnel>`).
* **Ephemeral storage:** on free container hosts without a persistent disk, a restart erases SQLite
  (findings, reports, Guard list, users). There is no seed-on-boot by design.

---

## 5. Debugging and troubleshooting playbook

### Health and status

```bash
curl -s localhost:8000/api/status | python3 -m json.tool      # mode (always live), heartbeats, counts
curl -s localhost:8000/api/healthz                           # 200 {ok:true}; 503 if the database is unreachable
curl -s localhost:8000/api/readiness | python3 -m json.tool   # admin (works with OPEN_ACCESS): registry, reputation, open access …
make doctor                                                  # can this machine reach RDAP, CT, the ranking list, a real page?
```

* API docs: `http://localhost:8000/docs` (dev only; switched off with `APP_ENV=production`).
* Logs: the terminal running `make dev`. Warnings at start-up show `OPEN_ACCESS`, failed ranking
  downloads and registry errors. `/dns-query` and verdict-page requests are deliberately **not** in
  the access log (privacy).
* There is no demo mode; `/api/mode` always reports `live`.

### Why did a link get this verdict?

```bash
make why URL="https://www.eand.ae/"      # verdict, every reason, every evidence source and its status
make trust-status                        # is the registry entry approved? is the ranking list loaded and fresh?
```

In any response read `tag`, `trust_reasons` / `reason_codes`, `domain_auth.status`
(`AUTHENTICATED`, `VERIFIED_ORGANIZATION`, `REPUTABLE_SITE`, `ESTABLISHED_SITE`, `UNLISTED`,
`PENDING`, `REVOKED`, `EXPIRED` …), `gov_verification.status`, `signals[]` (each with the part of the
input that triggered it) and `evidence[]` (what was checked, result, freshness).

* Genuine government / bank site shows WARNING → entry still `pending` (run `make setup-trust`) or
  no internet for RDAP/ranking (`make doctor`).
* RDAP failing or timing out → `domain_auth.established` / `evidence` show `unavailable`; a missing
  source is never treated as evidence. Turn off with `CHECK_RDAP_ENABLED=0`.

### Database, cache and storage

```bash
sqlite3 backend/data/daggers.db ".tables"
sqlite3 backend/data/daggers.db "SELECT id, domain, verdict, source, created_at FROM findings ORDER BY id DESC LIMIT 10;"
sqlite3 backend/data/daggers.db "SELECT domain, active, source, listed_at FROM guard_blocklist ORDER BY listed_at DESC LIMIT 10;"
sqlite3 backend/data/daggers.db "SELECT * FROM meta;"
```

Tables: `domains`, `findings`, `reports`, `sweep_runs`, `sweep_results`, `guard_hits`,
`guard_blocklist`, `guard_daily`, `guard_events`, `guard_pushed`, `feed_labels`, `feed_urls`, `meta`,
`users`, `sessions`, `audit_log`, `check_requests`. The Checker's own store
(`backend/data/checker-store.db`, created on first run) has `results`, `requests`, `meta`. `-wal` / `-shm` files next to a
database are normal (WAL mode).

Safe clearing (stop the server first):

| Problem | Command | Keeps |
|---|---|---|
| Checker returns an old stored result | `make reset-checker-store` | Portal data, registry approvals, evidence |
| Start completely empty | `make reset-local-data CONFIRM=yes` | code, registry approvals (`registry.yaml`), ranking list |
| Stale web app | Ctrl+Shift+R in the browser | — |

Stored Checker results are dropped automatically whenever code, rules, registry or ranking list
change (build fingerprint). Approvals live in `registry.yaml`, not in the database.

### Guard, NextDNS, DoH and AdGuard

```bash
curl -s localhost:8000/api/guard/stats | python3 -m json.tool     # counts, mode, dot_hostname, sync_health, newest_fakes
curl -s localhost:8000/api/guard/sync-status | python3 -m json.tool
curl -s localhost:8000/api/guard/blocklist.txt                  # hosts format (?format=domains for bare names)
curl -s "localhost:8000/api/guard/check?domain=example.com"     # is it listed?
curl -s -X POST localhost:8000/api/guard/sync                    # sync now (429 during the cooldown)
```

DoH test (run inside the project folder; `3` = blocked/NXDOMAIN, `0` = answered, `2` = upstream unreachable):

```bash
.venv/bin/python -c "
import base64,urllib.request
from backend.app.guard.doh import build_query
q=base64.urlsafe_b64encode(build_query('dubaipolice-fines-pay.top')).rstrip(b'=').decode()
r=urllib.request.urlopen('http://127.0.0.1:8000/dns-query?dns='+q).read(); print('rcode', r[3]&15)"
```

* `/dns-query` 404 → start with `GUARD_DOH_ENABLED=1`.
* Guard page says "Private DNS is not configured" → set `NEXTDNS_PROFILE_ID` (+ `NEXTDNS_API_KEY`
  for pushes) or `GUARD_DOT_HOSTNAME`, restart.
* "Sync error" / "Sync rate-limited" → read `sync-status` (wrong key/profile, HTTP 429, 5,000-entry
  NextDNS limit).
* Phone still opens a blocked site → its DNS cache: toggle Private DNS or airplane mode, or wait for
  the TTL; Chrome caches too.
* AdGuard Home: `make guard-sync` (dry run) / `make guard-sync APPLY=1`.

### Chrome extension

* `chrome://extensions` → Daggers Shield → **Errors**; **Inspect views: service worker** for
  `background.js` (network calls to `/api/scan`).
* Page console on the Google results page for `content/tagger.js`.
* Every label NOT CHECKED → backend unreachable or wrong URL in the popup; test
  `curl -s localhost:8000/api/healthz`. A failure must never show SAFE (covered by `make test-ext`).
* Non-localhost backend: HTTPS + the permission Chrome asks for; add the origin to `CORS_ORIGINS`.

### Radar, Vision and AI

* crt.sh slow/limited → keep `CRT_MIN_QUERY_GAP_S` ≥ 20; heartbeats in `/api/status` show the last run.
* No screenshots → `RENDER_ENABLED=1` and `make install-render`; below `RENDER_SCORE_MIN` nothing is rendered.
* AI answers look templated → no `GEMINI_KEY` / `GROQ_KEY`, provider failed, or `AI_PROVIDER=template`;
  responses carry `fallback: true`.

### Frontend and RTL

* `python3 ops/check_i18n.py` → missing EN/AR keys or hardcoded text.
* Separate static hosting → `window.API_BASE` in `web/config.js`; CORS on the server.
* Live updates stop → `curl -N localhost:8000/api/stream` should print `heartbeat` events; proxies
  must not buffer SSE (Caddy config does not).
* Old UI after an update → hard refresh (Ctrl+Shift+R); the service worker cache version is in `web/sw.js`.

---

## 6. Honest limitations, security boundaries and roadmap

**Integration status.** No WS1/WS2/WS3 patch is pending in this repository (see §3). Not
implemented: a demo mode and seed/fixture data (removed by design), a database of reported
phone numbers (the Number check uses pattern rules only), an OpenStreetMap maps fallback (the
`maps.py` docstring mentions it, but only Google Places is implemented), a precomputed pHash gallery
index (references are rendered on demand), MFA/SSO, password reset, multi-instance scaling, CI,
monitoring.

**External services.**

* NextDNS: denylist ≤ 5,000 entries, rate limits not published (Daggers backs off on 429), phones
  see NextDNS's plain block page; analytics depend on the plan.
* Branded verdict page needs the VPS path, and even then only **plain HTTP** visits see it: no
  server can hold a valid certificate for a scam domain, so HTTPS visits get a browser error (the
  scam still never loads).
* Android Private DNS needs DoT (port 853) — not available from a typical app host, hence NextDNS or
  a VPS.
* crt.sh, RDAP servers, Cert Spotter (hourly limit without `CT_API_KEY`), Serper, DuckDuckGo HTML,
  Google Places, Gemini and Groq all have quotas, rate limits or terms to respect. NextDNS,
  AdGuard Home, Serper, Places and the LLMs were tested only against mocked APIs.

**Chrome extension.** Not published on the Chrome Web Store; loaded with Developer mode. Google can
change its results markup at any time, which can break labelling.

**Registry and verification.** Entries ship `pending` and must be approved per installation;
approvals expire (`max_age_days`). Official sites may block automated retrieval (network, robots,
structure). Private businesses that are not approved, not widely used and not established get
WARNING. Domain age alone never makes a site SAFE — it must also have HTTPS, the same final site,
no feed listing and no warning signs.

**Security and privacy controls.** Passwords scrypt, HttpOnly SameSite=Strict sessions, CSRF on
every change, roles, login lockout, audit log, CSP and security headers, all SQL parameterised in
`backend/app/db/repo.py`. Zero-PII report evidence (validated); personal data removed from Checker messages; the
extension and `/api/scan` store nothing; DoH and the verdict page log no client IPs or names. Page
retrieval and official fetches: DNS resolved by Daggers, every address of every redirect hop must be
public (private, loopback, link-local, CGNAT … blocked), pinned connections, limited redirects.
Rendering never fills or submits forms and aborts non-GET requests. No secrets in the frontend or
extension. **`OPEN_ACCESS=1` removes sign-in for everyone** — demo use only. Full list:
[docs/SECURITY.md](docs/SECURITY.md).

**Roadmap (not started):** MFA/SSO, data-retention jobs, Postgres/Redis for several instances, CI
pipeline, monitoring/alerting, Chrome Web Store release, an official registry feed (instead of
reviewed public pages), branded HTTPS block page through a managed DNS provider.

---

## 7. Documentation map

| Document | Contents |
|---|---|
| [docs/API.md](docs/API.md) | API contract and verdict fields |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | architecture, data flows, database |
| [docs/CHECKER.md](docs/CHECKER.md) · [docs/CHECKER-ACCURACY.md](docs/CHECKER-ACCURACY.md) | the live Checker and its accuracy checks |
| [docs/GOVERNMENT-SAFE.md](docs/GOVERNMENT-SAFE.md) | government authentication and the SAFE policy |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/RUNBOOK.md](docs/RUNBOOK.md) | install, production, operations |
| [docs/SECURITY.md](docs/SECURITY.md) | security controls and limitations |
| [docs/TESTING-REPORT.md](docs/TESTING-REPORT.md) | what was tested and what was not |
| [docs/INTEGRATION-REPORT.md](docs/INTEGRATION-REPORT.md) | how WS1/WS2/WS3 were merged |
| [docs/WS2.md](docs/WS2.md) · [docs/WS2-README.md](docs/WS2-README.md) | trust policy, registry, channels, Guard |
| [docs/UI-KIT.md](docs/UI-KIT.md) | design system |
| [guard/README.md](guard/README.md) · [extension/README.md](extension/README.md) | Guard paths A/B · Chrome extension |

---

# العربية

<div dir="rtl">

## المحتويات

1. [التشغيل (4 خطوات)](#التشغيل-4-خطوات)
2. [نظرة عامة على المشروع — النظام الكامل](#1-نظرة-عامة-على-المشروع--النظام-الكامل)
3. [السرعة والأداء](#2-السرعة-والأداء)
4. [كيف تترابط الأجزاء](#3-كيف-تترابط-الأجزاء)
5. [الإعداد والاختبارات والنشر](#4-الإعداد-والاختبارات-والنشر)
6. [دليل تتبّع الأخطاء وحلّها](#5-دليل-تتبع-الأخطاء-وحلها)
7. [حدود صريحة وحدود الأمان وخطة العمل](#6-حدود-صريحة-وحدود-الأمان-وخطة-العمل)
8. [خريطة الوثائق](#7-خريطة-الوثائق)

## التشغيل (4 خطوات)

**المتطلبات:** لينكس أو macOS، الأداة `make`، **بايثون 3.11 أو أحدث**، واتصال بالإنترنت أثناء التثبيت
الأول. يلزم Node.js ومتصفح Google Chrome فقط للإضافة واختبارات المتصفح.

</div>

```bash
# 1. ادخل إلى مجلد المشروع داخل المستودع / الملف المضغوط
cd daggers-main            # المجلد الذي يحتوي Makefile و backend/ و web/

# 2. أنشئ .venv وثبّت الحزم بإصداراتها المثبّتة (من PyPI العام حتى لو كان الجهاز يستخدم مرآة خاصة)
make bootstrap PIP_INDEX=https://pypi.org/simple

# 3. اعتمد الجهات الرسمية والمؤسسات الموثّقة على هذا الجهاز، ونزّل قائمة الترتيب العالمية،
#    وامسح نتائج الفاحص المخزّنة، وشغّل الفحص الذاتي
make setup-trust

# 4. شغّل الخادم مع تفعيل محلّل DNS عبر HTTPS الخاص بالحارس
GUARD_DOH_ENABLED=1 make dev
```

<div dir="rtl">

ثم افتح (دون تسجيل دخول — راجع [الوصول المفتوح](#الوصول-المفتوح-دون-تسجيل-دخول)):

| الصفحة | العنوان |
|---|---|
| الفاحص | http://localhost:8000/#/check |
| فحص الرقم | http://localhost:8000/#/number |
| بوابة الشرطة (كل النتائج والبلاغات والذكاء الاصطناعي) | http://localhost:8000/#/portal |
| الحارس (قائمة الحظر المباشرة والإحصاءات وشريط الاختبار) | http://localhost:8000/#/guard |
| بثّ الرادار | http://localhost:8000/#/feed |
| المسح (البحث / الخرائط) | http://localhost:8000/#/sweep |
| صفحة الحكم | http://localhost:8000/verdict?domain=example.com |
| DNS عبر HTTPS | http://localhost:8000/dns-query (تُفعّله الخطوة 4) |

تجربة سريعة: افحص في الفاحص الرابط `https://dubaipolice-fines-pay.top/login` ← النتيجة **مزيّف (FAKE)**،
وتظهر خلال ثوانٍ في البوابة وفي قائمة «أحدث المواقع المزيّفة» في الحارس. أوقف الخادم بـ **Ctrl+C**.

ملاحظات:
* رسالة "Address already in use" تعني أن خادماً قديماً يعمل: `pkill -f "uvicorn backend.app.main"` أو
  `make dev PORT=8001`.
* أعد تشغيل `make setup-trust` بعد كل تحديث للكود (pull)، **ولا ترفع** الملف
  `backend/app/channels/official/registry.yaml` بعد الاعتماد (الاعتماد خاص بكل جهاز).
* يقرأ `make dev` ملف `.env` تلقائياً إن وُجد (`cp .env.example .env`).

### الوصول المفتوح (دون تسجيل دخول)

يضبط `make dev` القيمة `OPEN_ACCESS=1`: **كل زائر، من أي جهاز، يستخدم بوابة الشرطة بصفته المسؤول
`local` دون كلمة مرور** (قرار الفريق للعرض). تبقى التعديلات محمية برمز CSRF من نفس الموقع وتُسجَّل في سجل
التدقيق. أي شخص يصل إلى الموقع يستطيع قراءة بيانات البوابة وتعديلها — استخدمه فقط مع بيانات غير حساسة.
لإعادة الحسابات: `make dev OPEN_ACCESS=0` ثم `make user U=alice R=investigator` (الأدوار `viewer` <
`investigator` < `admin`) وسجّل الدخول من `#/login`.

---

## 1. نظرة عامة على المشروع — النظام الكامل

Daggers عملية FastAPI واحدة (`backend/app/main.py`) تخدم الواجهة البرمجية **وكذلك** تطبيق الويب ثنائي اللغة
من نفس الأصل، وقاعدة بياناتها SQLite بوضع WAL. كل الواجهات — الفاحص والرادار والمسح وبوابة الشرطة وإضافة
كروم والحارس — تأخذ حكمها من **عقل واحد** عبر **سياسة ثقة مركزية واحدة**. يوجد **وضع تشغيل واحد فقط:
مباشر (live)** — لا وضع عرض تجريبي، ولا بيانات أولية، ولا بيانات اختبار بديلة؛ التثبيت الجديد يبدأ فارغاً.

### الأحكام

| الوسم النهائي `tag` (ما تعرضه كل الواجهات) | المعنى |
|---|---|
| **آمن SAFE** | فقط عبر مسار معتمد: نطاق رسمي معتمد وحديث الاعتماد في السجل الرسمي (الفئة A/B)، أو وسيلة إعلام معتمدة (C) أو مؤسسة موثّقة (P)، أو موقع واسع الاستخدام من قائمة Tranco (`REPUTATION_TOP_N`، افتراضياً 60,000)، أو موقع راسخ (مسجّل منذ 730 يوماً على الأقل حسب RDAP، مع HTTPS، ودون علامات تحذير) — ودائماً دون أي شيء مريب |
| **تحذير WARNING** | غير معروف، أو غير موثّق، أو تعذّر فحصه، أو مريب دون تأكيد. **المجهول لا يصبح آمناً أبداً.** |
| **مضلّل MISLEADING** | ادّعاء حكومي أو مؤسسي تناقضه المصادر المعتمدة أو لا يمكن التحقق منه منها؛ عروض لا يمكن التحقق منها |
| **مزيّف FAKE** | احتيال أو تصيّد أو انتحال مدعوم بأدلة كافية |

يُحتفظ بحكم المحرّك (`verdict`: `MALICIOUS / MISLEADING / SUSPICIOUS / UNKNOWN`) للتوافق فقط؛ المرجع هو
`tag`. نسخة السياسة `daggers-trust-2.2` ونسخة المحرّك `daggers-engine-3.1`.

### الأجزاء الثمانية

| # | الجزء | المكان | ما يفعله (مُنفّذ) |
|---|---|---|---|
| 1 | **العقل المركزي** | `backend/app/core/` و `backend/app/channels/{scoring,trust_policy,reputation,established}.py` و `backend/app/channels/official/` و `backend/app/intel/` | مقيّم حتمي (`scorer.py`): توحيد الروابط والنطاقات الدولية IDN، إشارات لفظية وإشارات هوية، تقليد العلامات التجارية، كشف **الحروف المتشابهة والانتحال البصري** (`homograph.py` والبيانات في `rules.yaml`)، تحليل **الادعاءات والطُعوم** بالإنجليزية والعربية والعربيزي (`claims.py` و `lures.yaml`)، تحليل الرسائل (`message.py`: طلب رمز التحقق أو البطاقة، طلب الدفع، طُعوم التوصيل، الاستعجال، الانتحال)، وقواعد أرقام الهاتف (`numbers.py`، يستخدمها **فحص الرقم** وقوائم الخرائط). **سجل** المصادر الإماراتية الرسمية (`registry.yaml` وأداة سطر الأوامر) و**التحقق من الادعاءات** مقابل سجلات معتمدة (`official/verify.py` و `compare.py`). أدلة مباشرة للفاحص: عمر النطاق عبر RDAP، شفافية الشهادات، قراءة آمنة للصفحة، قوائم التهديدات (`intel/`). السياسة المركزية `trust_policy.decide()` مع رموز الأسباب. |
| 2 | **الرادار والرؤية** | `backend/app/radar/` و `backend/app/vision/` | متابعة سجلات شفافية الشهادات عبر crt.sh (`crt.py`)، قوائم التهديد OpenPhish و URLhaus و PhishTank بمفتاح (`feeds.py`)، إثراء RDAP و DNS و TLS والأيقونة، كلٌّ بمهلة زمنية مستقلة (`enrich.py`)، وخط المعالجة (`pipeline.py`). الرؤية: لقطات شاشة عبر Playwright بمهلة صارمة تُلغي كل طلب غير GET ولا تملأ أي نموذج (`render.py`)، ومقارنة استنساخ ORB + RANSAC عند توفّر OpenCV وإلا البصمة الإدراكية (`diff.py` و `gallery.py`)، وصور أدلة مُعلَّمة، و OCR اختياري عبر Tesseract (`ocr.py`). **كلها متوقفة افتراضياً** (`CRT_ENABLED` و `FEEDS_ENABLED` و `ENRICH_ENABLED` و `RENDER_ENABLED`)، وحزم الرؤية اختيارية (`make install-render`). |
| 3 | **الفاحص** | `POST /api/check` و `backend/app/checker.py` و `web/js/views/check.js` | الصق **رابطاً أو نطاقاً أو رسالة**. يصنّف المدخل ويوحّده ويشغّل العقل مع الأدلة المباشرة (`CHECK_EVIDENCE_DEADLINE_S`)، ويزيل البيانات الشخصية من الرسائل، و**يرسل** كل نتيجة جديدة إلى بوابة الشرطة كنتيجة بمصدر `checker`، ويحتفظ **بمخزن نتائج خاص به** (`CHECKER_STORE_PATH`، يُعاد استخدامه طوال `CHECK_CACHE_TTL_S`). يُستعاد السجل بعد إغلاق المتصفح. **فحص الرقم** (`#/number` و `POST /api/number` و `web/js/views/number.js`): يُفحص رقم الهاتف الذي اتصل بك أو راسلك بقواعد دون اتصال (الأرقام المميزة مدفوعة الأجر، معاودة الاتصال/الإنترنت، التكرار، فهرس الأنماط)؛ لا يكون «آمناً» أبداً (عدم وجود علامات = «تحذير» أي غير موثّق)؛ و**لا يُخزَّن شيء**. |
| 4 | **المسح** | `backend/app/channels/{search,maps,sweep}.py` و `POST /api/sweep` | بحث الويب عبر Serper (بمفتاح) و DuckDuckGo عند `SEARCH_LIVE_ENABLED=1`؛ الخرائط عبر Google Places عند `MAPS_LIVE_ENABLED=1` مع المفتاح. كل نتيجة تمر بنفس العقل والسياسة؛ النتائج المزيّفة أو المضلّلة تصبح نتائج في البوابة. يعمل في الخلفية (202 مع متابعة الحالة). لا بيانات اختبار في التشغيل — دون مزوّد يفشل المسح بوضوح. |
| 5 | **الحارس** | `backend/app/guard/` و `backend/app/api/guard.py` و `guard/` | حظر مباشر على مستوى DNS **للنطاقات المزيّفة فقط**. فحوص روابط الفاحص والرادار والمسح والتحقيقات تغذّي فهرساً في الذاكرة بزمن O(1) محفوظاً في SQLite. يوفّر قوائم بصيغ hosts و domains و AdGuard، و**محلّل DoH** وفق RFC 8484 على `/dns-query`، وصفحة حكم ثنائية اللغة `/verdict`، وإحصاءات مباشرة وأحداث SSE باسم `guard`؛ ويدفع إلى قائمة المنع في **NextDNS** (مفتاح وملف تعريف)؛ وأداة جانبية للخادم الخاص مع **AdGuard Home** و nginx (`guard/sync.py` و `guard/nginx-verdict.conf`). لا يحظر أبداً التحذير أو المجهول أو عناوين IP أو النطاقات الحكومية أو نطاقات السجل أو النطاقات الرسمية للعلامات أو المنصات المشتركة أو المواقع واسعة الاستخدام. |
| 6 | **إضافة كروم (MV3)** | `extension/` | تضع وسم الخادم `tag` على نتائج Google **العضوية** (google.com و google.ae) عبر `POST /api/scan`؛ تتجاهل الإعلانات وحزم الخرائط والدوّارات؛ وتتعامل مع النتائج المتغيرة عبر `MutationObserver`. عند الفشل: **NOT CHECKED** رمادي، ولا «آمن» أبداً. الصلاحيات: `storage` و localhost (أي خادم آخر يُطلب له إذن مستقل). لا تجمع سجل التصفح. |
| 7 | **بوابة الشرطة والأدلة والمحلّل الذكي** | `web/js/views/portal.js` و `backend/app/api/{investigations,reports,ai}.py` و `backend/app/reports/` و `backend/app/ai/` | فهرس قابل للبحث لكل النتائج؛ تحقيقات؛ بلاغات بأدلة **خالية من البيانات الشخصية** (يتم التحقق منها) ودورة حياة `QUEUED → SUBMITTED → SEEN`؛ تقديم تلقائي للمواقع شديدة التشابه (`AUTOFILE_CLONE_MIN`)؛ حزمة تصدير؛ سجل تدقيق. المحلّل الذكي **Gemini → Groq → قالب حتمي** لملخصات القضايا ومسودات طلبات الإزالة بالعربية والإنجليزية — يشرح الأدلة المخزّنة و**لا يقرّر الحكم أبداً**. |
| 8 | **تطبيق ويب تقدّمي ثنائي اللغة** | `web/` | واجهة فاتحة بأسلوب Neo-Outline Soft، عربية وإنجليزية كاملة مع اتجاه من اليمين لليسار (`web/js/i18n/en.json` و `ar.json` مع فرض تطابق المفاتيح)، بثّ مباشر عبر SSE، قابل للتثبيت؛ عامل الخدمة يخزّن هيكل التطبيق وقراءات الواجهة البرمجية **العامة** فقط. |

---

## 2. السرعة والأداء

### قياسات فعلية

الأمر `make bench` (`ops/bench.py`) — مسارات دون اتصال فقط، بقاعدة بيانات مؤقتة ودون شبكة. قيس بتاريخ
2026-11-25 على جهاز البناء (معالجان، بايثون 3.13) على هذا الكود:

</div>

| العملية / Operation | الوسيط / Median | p95 |
|---|---|---|
| فحص دون اتصال: العقل + السياسة المركزية (مسار `/api/scan` للإضافة)، n = 200 | 4.16 ms | 6.17 ms |
| بحث الحارس، 50,000 نطاق مدرج، مطابقة الموقع الأب | 8.8 µs | 11.3 µs |
| بحث الحارس، اسم غير مدرج | 2.9 µs | 3.9 µs |
| رد DoH لاسم محظور (تحليل + بحث + رد) | 13.3 µs | 19.3 µs |

<div dir="rtl">

ستختلف الأرقام حسب الجهاز — شغّل `make bench`. لا نزعم أي رقم زمني آخر. أدلة الفاحص المباشرة (RDAP والصفحة
والشهادات) تعتمد على الشبكة ومحدودة بـ `CHECK_EVIDENCE_DEADLINE_S` (افتراضياً 10 ثوانٍ).

### لماذا هو سريع (التصميم)

* **عقل حتمي دون شبكة في الطبقة غير المتصلة.** القواعد والمعجم والحروف المتشابهة والادعاءات تعمل في الذاكرة؛
  `/api/scan` (الإضافة) والمسح لا يجريان أي اتصال خارجي لكل نتيجة.
* **فهرس الحارس O(1)** (قاموس مع صعود إلى الموقع الأب) يُحمَّل من SQLite (WAL) عند بدء التشغيل؛ وعمليات
  الدفع إلى المزوّد **تُجمَّع** (`GUARD_SYNC_DEBOUNCE_S`) في مزامنة واحدة.
* **عزل المهل الزمنية.** إثراء الرادار يغلّف RDAP و DNS و TLS والأيقونة كلّاً بـ `asyncio.wait_for`؛ وأدلة
  الفاحص المباشرة تتقاسم مهلة واحدة؛ وللّقطات مهلة صارمة. المصدر البطيء أو الفاشل يصبح «غير متاح» ولا يعطّل الطلب.
* **رؤية مشروطة بالدرجة.** اللقطات تعمل فقط عند `RENDER_ENABLED=1` **و** درجة ≥ `RENDER_SCORE_MIN` (0.45) أو
  حكم مضلّل/خبيث. لقطات المرجع تُلتقط عند الحاجة في `GALLERY_DIR`؛ و ORB+RANSAC فقط عند توفّر OpenCV.
* **أحداث الخادم المرسلة** (`/api/stream`: `finding` و `sweep` و `guard` و `heartbeat`) — دون استطلاع متكرر.
* **تخزين مؤقت مع إبطال صحيح.** مخزن نتائج الفاحص (6 ساعات / 10 دقائق للنتائج الجزئية) مفتاحه نسخ المحرّك
  والسياسة والسجل والسمعة وبصمة البناء، فأي تغيير في الكود أو البيانات يعيد التحليل؛ وتخزين مؤقت للبحث؛ وتخزين
  RDAP في الذاكرة؛ وتخزين ردود DoH لـ 30 ثانية؛ وتخزين النتائج داخل الإضافة.

---

## 3. كيف تترابط الأجزاء

</div>

```
 Browser PWA + Police Portal      Chrome extension (MV3)     Phones / routers / NextDNS / AdGuard Home
        │ same origin                    │ POST /api/scan          │ /dns-query · lists · /verdict
        ▼                                ▼                         ▼
 ┌──────────────── FastAPI app  backend/app/main.py  (Caddy HTTPS in production) ─────────────────┐
 │ routers: auth · system · examples · check · findings · scan · health · stream · investigations │
 │          reports · ai · sweep · guard                                                          │
 │ Runtime ── ONE verdict path: core/scorer → channels/scoring.ShieldScorer → trust_policy.decide │
 │ radar/ → vision/ · channels/ search·maps·sweep · reports/ · ai/ · guard/ · checker_store/       │
 │ db/repo.py — ALL SQL — SQLite WAL                                                              │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

<div dir="rtl">

### مسارات البيانات الخمسة (كما هي موصولة في الكود)

1. **الرادار** — crt.sh وقوائم التهديد ← الإثراء (بمهل زمنية) ← العقل ← الرؤية اختيارياً (حسب الدرجة) ← نتيجة في
   SQLite ← حدث SSE `finding` ← بلاغ تلقائي عندما تبلغ درجة الاستنساخ `AUTOFILE_CLONE_MIN` ← الحارس (المزيّف فقط)
   مع حدث SSE `guard`.
2. **الفاحص** — `POST /api/check` ← التصنيف والتوحيد ← العقل + الأدلة المباشرة + التحقق من الادعاءات الرسمية ←
   سياسة الثقة ← إزالة البيانات الشخصية ← إرسال النتيجة إلى البوابة وإلى المخزن الخاص ← فحوص **الروابط**
   المزيّفة تُدرج في الحارس فوراً (والرد يحمل الحقل `guard`). الإضافة تستخدم `POST /api/scan`: نفس العقل والسياسة،
   **دون تخزين ودون إدراج**.
3. **المسح** — `POST /api/sweep` (202) ← تشغيل في الخلفية ← Serper/DuckDuckGo أو Google Places ← العقل والسياسة
   لكل نتيجة ← تخزين النتائج ← المزيّف والمضلّل يصبحان نتائج ← حدث SSE `sweep` ← النطاقات المزيّفة إلى الحارس.
4. **البلاغ ← الذكاء الاصطناعي** — `POST /api/reports` يبني أدلة خالية من البيانات الشخصية من النتيجة (مع التحقق) ←
   `POST /api/report/{id}/analysis` (بثّ) و `/takedown` يُبنيان في الخادم من الأدلة المخزّنة ← يُحفظان في البلاغ ←
   البوابة؛ دورة الحياة عبر `/api/reports/{id}/advance` وحزمة التصدير عبر `/export`.
5. **الحارس** — الأهلية (المزيّف فقط ورفض النطاقات المحمية) ← فهرس O(1) وجدول `guard_blocklist` ←
   `/api/guard/feed` و `blocklist.txt` و `domains.txt` و `adguard-rules.txt` و `/dns-query` والدفع إلى NextDNS
   (مجمّع مع مهلة تهدئة للمزامنة اليدوية) والأداة الجانبية لـ AdGuard Home ← صفحة الحارس (SSE) و `/verdict`.

### عقود الواجهات وحدود مسارات العمل

يشير الكود إلى هذه العقود: **C1** شكل النتيجة (`backend/app/db/repo.py` و `backend/app/api/findings.py`؛ أدلة البلاغ = C1 + الوسم +
`evidence_id`)، و **C4** دورة حياة البلاغ (`backend/app/reports/queue.py`)، و **C6** صف قائمة الحارس
`{domain, verdict, reason, flagged_at}` (`backend/app/guard/manager.py`). مواصفة مسارات العمل الأصلية التي تعرّف C2 و C3
و C5 و C7 **غير موجودة في هذا المستودع**، لذلك لا نوثّقها هنا. عقد الواجهة البرمجية الكامل في
[docs/API.md](docs/API.md).

| مسار العمل | يملك | الحالة ([docs/INTEGRATION-REPORT.md](docs/INTEGRATION-REPORT.md)) |
|---|---|---|
| WS1 محرّك الذكاء | `core/` و `radar/` و `vision/` و `db/` و `main.py` | أساس الدمج؛ صُحّح تحويل الواجهة من `UNKNOWN → SAFE` إلى `UNKNOWN → WARNING` |
| WS2 الدرع والقنوات | `channels/` (سياسة الثقة، السجل، التحقق، البحث، الخرائط، المسح) و `guard/` و `extension/` | رقعه الخمس على WS1 (0001–0005) **مطبّقة**، وأزيل مجلد `patches/` |
| WS3 الواجهة والمحلّل | `web/` و `ai/` ومسارات البلاغات والذكاء الاصطناعي | دُمج على مستودع WS1؛ وأزيل الخادم البديل والمخزن في الذاكرة الخاصّان بـ WS3 |

لا توجد رقعة دمج معلّقة في هذا المستودع. ما زال يحتاج **تدخّلاً بشرياً**: اعتماد السجل على كل جهاز
(`make setup-trust`) والحسابات الخارجية المذكورة في القسم 6.

---

## 4. الإعداد والاختبارات والنشر

### المتطلبات

| المطلوب | الغرض |
|---|---|
| بايثون **3.11+** والأداة `make` | كل شيء (`make bootstrap` يتحقق من الإصدار) |
| Node.js (اختُبر بالإصدار 22) | `make test-ext` و `make gates` واختبارات المتصفح |
| Google Chrome و Playwright | الإضافة واختبارات المتصفح `make e2e*` |
| اختياري: `make install-render` (Playwright Chromium و OpenCV و imagehash و NumPy و pytesseract) | لقطات الرادار وكشف الاستنساخ |

### الإعداد (`.env`)

نفّذ `cp .env.example .env` ثم عدّل؛ لكل مفتاح قيمة افتراضية آمنة و**لا يلزم أي مفتاح للتشغيل**. لا ترفع
`.env` أبداً. المجموعات الرئيسية (كل الأسماء موجودة في `.env.example`):

</div>

| المجال / Area | المتغيرات / Variables |
|---|---|
| البيئة والوصول | `APP_ENV` (`dev`/`production`), `PORT`, `OPEN_ACCESS`, `LOCAL_OPEN_ACCESS`, `COOKIE_SECURE`, `SESSION_TTL_HOURS`, `LOGIN_MAX_FAILURES`, `SCAN_RATE_PER_MIN`, `TRUST_PROXY_HEADERS`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` |
| التخزين | `DB_PATH`, `EVIDENCE_DIR`, `GALLERY_DIR`, `CHECKER_STORE_PATH`, `OFFICIAL_REGISTRY_PATH`, `OFFICIAL_SNAPSHOT_DIR`, `WEB_DIR` |
| الفاحص | `CHECK_CACHE_TTL_S`, `CHECK_CACHE_PARTIAL_TTL_S`, `CHECK_RDAP_ENABLED`, `CHECK_PAGE_FETCH_ENABLED`, `CHECK_CT_ENABLED`, `CHECK_EVIDENCE_DEADLINE_S`, `CT_API_URL`, `CT_API_KEY` |
| السمعة | `REPUTATION_LIST_PATH`, `REPUTATION_AUTO_UPDATE`, `REPUTATION_TOP_N`, `REPUTATION_MAX_AGE_DAYS` |
| عتبات المحرّك | `MALICIOUS_THRESHOLD`, `SUSPICIOUS_THRESHOLD`, `RENDER_SCORE_MIN`, `AUTOFILE_CLONE_MIN` |
| الرادار | `CRT_ENABLED`, `FEEDS_ENABLED`, `ENRICH_ENABLED`, `RENDER_ENABLED`, `PHISHTANK_KEY`, `HTTP_TIMEOUT_S`, `HTTP_USER_AGENT`, `CRT_MIN_QUERY_GAP_S`, `CRT_POLL_INTERVAL_S`, `FEED_POLL_INTERVAL_S`, `PIPELINE_POLL_INTERVAL_S`, `HEARTBEAT_INTERVAL_S` |
| المسح | `SEARCH_LIVE_ENABLED`, `SERPER_API_KEY`, `MAPS_LIVE_ENABLED`, `GOOGLE_PLACES_API_KEY`, `SWEEP_ALLOW_ARBITRARY`, `SWEEP_RATE_PER_MIN`, `SWEEP_MAX_CONCURRENT` |
| الحارس | `GUARD_ENABLED`, `GUARD_MAX_AGE_DAYS`, `GUARD_INCLUDE_MISLEADING` (الاسم القديم `GUARD_BLOCK_MISLEADING`), `GUARD_SOURCES`, `GUARD_SYNC_DEBOUNCE_S`, `GUARD_SYNC_COOLDOWN_S`, `GUARD_PUBLIC_ORIGIN`, `GUARD_DOH_ENABLED`, `GUARD_UPSTREAM_DOH`, `GUARD_DOH_BLOCK_MODE`, `GUARD_DOH_RATE_PER_MIN`, `GUARD_VERDICT_IP`, `NEXTDNS_PROFILE_ID`, `NEXTDNS_API_KEY`, `GUARD_DOT_HOSTNAME` |
| الذكاء الاصطناعي | `AI_PROVIDER` (`auto`/`gemini`/`groq`/`template`), `AI_ON`, `AI_STATE`, `GEMINI_KEY`, `GROQ_KEY` |
| Docker/Caddy | `DAGGERS_DOMAIN` |

<div dir="rtl">

### السجل الرسمي (سطر الأوامر)

كل إدخال **يُشحن بحالة `pending`**؛ لا شيء يصبح آمناً عبر السجل قبل اعتماده على جهازك.

</div>

```bash
make setup-trust                                  # اعتماد كل الإدخالات الموثّق تحققها (+ قائمة الترتيب + الفحص الذاتي)
make approve-verified                             # خطوة الاعتماد وحدها
make registry ARGS="list --status pending"        # list / show / validate
make registry ARGS="approve wam"                  # إدخال واحد (اسم المراجِع اختياري: --reviewer "Name")
make registry ARGS="revoke wam"                   # سحب الاعتماد
make registry ARGS="fetch wam"                    # جلب السجلات الرسمية إلى OFFICIAL_SNAPSHOT_DIR (يحتاج شبكة)
make trust-status                                 # حالة اعتماد السجل وقائمة الترتيب
make reputation-update                            # تنزيل قائمة Tranco للمواقع الأكثر استخداماً
```

<div dir="rtl">

### إضافة كروم

`chrome://extensions` ← **وضع المطوّر** ← **تحميل إضافة غير مضغوطة** ← اختر المجلد `extension/`. والخادم يعمل
على `http://localhost:8000`، ابحث في google.com أو google.ae. غيّر عنوان الخادم من النافذة المنبثقة للإضافة
(يلزم HTTPS إلا لـ localhost). التفاصيل: [extension/README.md](extension/README.md).

### الاختبارات

</div>

```bash
make check                       # تجميع + اختبارات الخادم + اختبارات الإضافة + بوابات اللغة والصياغة
make test                        # الخادم: pytest backend/tests -q
make test-ext                    # منطق الإضافة (node --test)
make gates                       # تطابق مفاتيح العربية/الإنجليزية، لا نصوص ثابتة، صياغة JS
make bench                       # قياس زمني دون اتصال (القسم 2)
make verify-empty                # التثبيت الجديد لا يحتوي بيانات

# اختبارات محددة
.venv/bin/python -m pytest backend/tests/test_guard_live.py -q          # الحارس
.venv/bin/python -m pytest backend/tests/test_gov_safe.py -q            # الأمان الحكومي / السجل
.venv/bin/python -m pytest backend/tests/test_checker.py -q             # سيناريوهات الفاحص
.venv/bin/python -m pytest backend/tests/ws2 -q                         # سياسة الثقة والقنوات WS2
.venv/bin/python -m pytest backend/tests/ws3 -q                         # الذكاء الاصطناعي WS3
```

<div dir="rtl">

اختبارات المتصفح (Chrome حقيقي مقابل خادم يعمل؛ `make dev` في طرفية أخرى):
`make e2e PORTAL_USER=… PORTAL_PASS=…` (ابدأ الخادم بـ `OPEN_ACCESS=0` وأنشئ المستخدم أولاً)، و
`make e2e-guard`، و `make e2e-gov …`، و `make e2e-rep …`، و `make e2e-restore PHASE=1|2` — راجع التعليقات في
`Makefile`.

**آخر تشغيل على هذا الكود (2026-11-25):** الخادم **454 ناجحاً**، الإضافة **10/10**، البوابات سليمة،
`make e2e` **35/35**، `make e2e-guard` **19/19**. التشغيلات السابقة والثغرات:
[docs/TESTING-REPORT.md](docs/TESTING-REPORT.md).

### النشر

* **المُنفّذ: Docker Compose مع Caddy و HTTPS** (`Dockerfile` و `docker-compose.yml` و `deploy/Caddyfile`). اضبط
  `DAGGERS_DOMAIN` و `CORS_ORIGINS` في `.env` ثم `docker compose up -d --build`. البيانات في المجلد الدائم
  `daggers-data`. الخطوات الكاملة والنسخ الاحتياطي والتراجع: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). لم تُبنَ
  الصورة في بيئة اختبارنا.
* **الحارس، المسار A (دون خادم خاص):** أي استضافة HTTPS لـ Daggers + NextDNS (`NEXTDNS_PROFILE_ID` و
  `NEXTDNS_API_KEY`) + DoH اختيارياً. **المسار B (خادم خاص):** AdGuard Home مع خادم صفحة الحكم nginx
  (`guard/AdGuardHome.yaml.example` و `guard/nginx-verdict.conf` و `make guard-sync`). راجع
  [guard/README.md](guard/README.md).
* **استضافة الواجهة منفصلة:** يحدّد `web/config.js` قيمة `window.API_BASE`. لا يحتوي المستودع **أي** إعداد جاهز
  لـ Hugging Face Spaces أو Render أو Cloudflare Pages.
* **عرض على الهاتف دون استضافة:** نفق HTTPS مؤقت مثل `cloudflared tunnel --url http://localhost:8000`، ثم استخدم
  `https://<tunnel>/dns-query` كـ DNS آمن مخصّص في Chrome على أندرويد (وشغّل الخادم مع
  `GUARD_PUBLIC_ORIGIN=https://<tunnel>`).
* **التخزين المؤقت للحاويات:** على الاستضافات المجانية دون قرص دائم، إعادة التشغيل تمسح SQLite (النتائج والبلاغات
  وقائمة الحارس والمستخدمين). لا توجد بيانات أولية عند الإقلاع، وذلك مقصود.

---

## 5. دليل تتبع الأخطاء وحلها

### الصحة والحالة

</div>

```bash
curl -s localhost:8000/api/status | python3 -m json.tool      # الوضع (دائماً live)، النبضات، الأعداد
curl -s localhost:8000/api/healthz                           # 200 {ok:true}؛ 503 إذا تعذّر الوصول إلى قاعدة البيانات
curl -s localhost:8000/api/readiness | python3 -m json.tool   # للمسؤول (يعمل مع OPEN_ACCESS): السجل، السمعة، الوصول المفتوح …
make doctor                                                  # هل يصل هذا الجهاز إلى RDAP والشهادات وقائمة الترتيب وصفحة حقيقية؟
```

<div dir="rtl">

* توثيق الواجهة البرمجية: `http://localhost:8000/docs` (في وضع التطوير فقط؛ يُطفأ مع `APP_ENV=production`).
* السجلات: الطرفية التي تشغّل `make dev`. تظهر عند الإقلاع تحذيرات `OPEN_ACCESS` وفشل تنزيل قائمة الترتيب وأخطاء
  السجل. طلبات `/dns-query` وصفحة الحكم **لا** تُسجَّل في سجل الوصول عمداً (للخصوصية).
* لا يوجد وضع عرض تجريبي؛ و `/api/mode` يعيد دائماً `live`.

### لماذا حصل الرابط على هذا الحكم؟

</div>

```bash
make why URL="https://www.eand.ae/"      # الحكم، كل سبب، وكل مصدر دليل وحالته
make trust-status                        # هل الإدخال معتمد؟ هل قائمة الترتيب محمّلة وحديثة؟
```

<div dir="rtl">

في أي رد اقرأ `tag` و `trust_reasons` / `reason_codes` و `domain_auth.status` (`AUTHENTICATED` و
`VERIFIED_ORGANIZATION` و `REPUTABLE_SITE` و `ESTABLISHED_SITE` و `UNLISTED` و `PENDING` و `REVOKED` و `EXPIRED` …)
و `gov_verification.status` و `signals[]` (كل إشارة مع جزء المدخل الذي أطلقها) و `evidence[]` (ما فُحص والنتيجة
وحداثتها).

* موقع حكومي أو بنكي حقيقي يظهر «تحذير» ← الإدخال ما زال `pending` (شغّل `make setup-trust`) أو لا يوجد إنترنت
  لـ RDAP/قائمة الترتيب (`make doctor`).
* فشل RDAP أو انتهاء مهلته ← يظهر `unavailable` في `domain_auth.established` و `evidence`؛ المصدر المفقود لا يُعدّ
  دليلاً أبداً. للإيقاف: `CHECK_RDAP_ENABLED=0`.

### قاعدة البيانات والتخزين المؤقت

</div>

```bash
sqlite3 backend/data/daggers.db ".tables"
sqlite3 backend/data/daggers.db "SELECT id, domain, verdict, source, created_at FROM findings ORDER BY id DESC LIMIT 10;"
sqlite3 backend/data/daggers.db "SELECT domain, active, source, listed_at FROM guard_blocklist ORDER BY listed_at DESC LIMIT 10;"
sqlite3 backend/data/daggers.db "SELECT * FROM meta;"
```

<div dir="rtl">

الجداول: `domains` و `findings` و `reports` و `sweep_runs` و `sweep_results` و `guard_hits` و `guard_blocklist` و
`guard_daily` و `guard_events` و `guard_pushed` و `feed_labels` و `feed_urls` و `meta` و `users` و `sessions` و
`audit_log` و `check_requests`. مخزن الفاحص الخاص (`backend/data/checker-store.db`، يُنشأ عند أول تشغيل) فيه `results` و `requests` و
`meta`. ملفات `-wal` و `-shm` بجانب قاعدة البيانات طبيعية (وضع WAL).

المسح الآمن (أوقف الخادم أولاً):

| المشكلة | الأمر | ما يبقى |
|---|---|---|
| الفاحص يعيد نتيجة قديمة مخزّنة | `make reset-checker-store` | بيانات البوابة، اعتمادات السجل، الأدلة |
| البدء من الصفر تماماً | `make reset-local-data CONFIRM=yes` | الكود، اعتمادات السجل (`registry.yaml`)، قائمة الترتيب |
| واجهة ويب قديمة | Ctrl+Shift+R في المتصفح | — |

تُحذف نتائج الفاحص المخزّنة تلقائياً عند أي تغيير في الكود أو القواعد أو السجل أو قائمة الترتيب (بصمة البناء).
الاعتمادات محفوظة في `registry.yaml` وليس في قاعدة البيانات.

### الحارس و NextDNS و DoH و AdGuard

</div>

```bash
curl -s localhost:8000/api/guard/stats | python3 -m json.tool     # الأعداد، الوضع، dot_hostname، sync_health، newest_fakes
curl -s localhost:8000/api/guard/sync-status | python3 -m json.tool
curl -s localhost:8000/api/guard/blocklist.txt                  # صيغة hosts (‎?format=domains للأسماء فقط)
curl -s "localhost:8000/api/guard/check?domain=example.com"     # هل النطاق مدرج؟
curl -s -X POST localhost:8000/api/guard/sync                    # زامن الآن (429 أثناء مهلة التهدئة)
```

<div dir="rtl">

اختبار DoH (شغّله داخل مجلد المشروع؛ `3` = محظور/NXDOMAIN، `0` = أُجيب، `2` = الخادم الأعلى غير متاح):

</div>

```bash
.venv/bin/python -c "
import base64,urllib.request
from backend.app.guard.doh import build_query
q=base64.urlsafe_b64encode(build_query('dubaipolice-fines-pay.top')).rstrip(b'=').decode()
r=urllib.request.urlopen('http://127.0.0.1:8000/dns-query?dns='+q).read(); print('rcode', r[3]&15)"
```

<div dir="rtl">

* `/dns-query` يعيد 404 ← شغّل مع `GUARD_DOH_ENABLED=1`.
* صفحة الحارس تقول «DNS الخاص غير مُعدّ» ← اضبط `NEXTDNS_PROFILE_ID` (و `NEXTDNS_API_KEY` للدفع) أو
  `GUARD_DOT_HOSTNAME` ثم أعد التشغيل.
* «خطأ في المزامنة» أو «المزامنة محدودة» ← اقرأ `sync-status` (مفتاح أو ملف تعريف خاطئ، HTTP 429، حدّ 5,000
  إدخال في NextDNS).
* الهاتف ما زال يفتح موقعاً محظوراً ← ذاكرة DNS المؤقتة: أوقف DNS الخاص وشغّله، أو وضع الطيران، أو انتظر انتهاء
  مدة الصلاحية؛ وكروم يخزّن أيضاً.
* AdGuard Home: `make guard-sync` (تجربة دون تغيير) / `make guard-sync APPLY=1`.

### إضافة كروم

* `chrome://extensions` ← Daggers Shield ← **Errors**؛ و **Inspect views: service worker** لملف `background.js`
  (طلبات `/api/scan`).
* وحدة تحكم الصفحة في صفحة نتائج Google لملف `content/tagger.js`.
* كل الوسوم NOT CHECKED ← الخادم غير متاح أو العنوان خاطئ في النافذة المنبثقة؛ اختبر
  `curl -s localhost:8000/api/healthz`. الفشل لا يجوز أن يظهر «آمن» أبداً (يغطيه `make test-ext`).
* خادم غير localhost: يلزم HTTPS والإذن الذي يطلبه كروم؛ وأضف الأصل إلى `CORS_ORIGINS`.

### الرادار والرؤية والذكاء الاصطناعي

* crt.sh بطيء أو محدود ← أبقِ `CRT_MIN_QUERY_GAP_S` ≥ 20؛ النبضات في `/api/status` تُظهر آخر تشغيل.
* لا لقطات شاشة ← `RENDER_ENABLED=1` و `make install-render`؛ ولا لقطات تحت `RENDER_SCORE_MIN`.
* ردود الذكاء الاصطناعي تبدو قالباً ← لا يوجد `GEMINI_KEY` / `GROQ_KEY`، أو فشل المزوّد، أو `AI_PROVIDER=template`؛
  والردود تحمل `fallback: true`.

### الواجهة والاتجاه من اليمين لليسار

* `python3 ops/check_i18n.py` ← مفاتيح ناقصة بين العربية والإنجليزية أو نصوص ثابتة.
* استضافة الواجهة منفصلة ← `window.API_BASE` في `web/config.js` مع CORS في الخادم.
* توقف التحديثات المباشرة ← يجب أن يطبع `curl -N localhost:8000/api/stream` أحداث `heartbeat`؛ ويجب ألا يخزّن
  الوسيط أحداث SSE (إعداد Caddy لا يخزّنها).
* واجهة قديمة بعد التحديث ← تحديث قسري (Ctrl+Shift+R)؛ ونسخة ذاكرة عامل الخدمة في `web/sw.js`.

---

## 6. حدود صريحة وحدود الأمان وخطة العمل

**حالة الدمج.** لا توجد رقعة معلّقة لـ WS1/WS2/WS3 في هذا المستودع (القسم 3). غير مُنفّذ: وضع العرض التجريبي والبيانات
الأولية/بيانات الاختبار (أزيلت عمداً)، قاعدة بيانات لأرقام هاتف مُبلَّغ عنها (فحص الرقم يستخدم قواعد الأنماط فقط)،
بديل خرائط OpenStreetMap (تذكره تعليقات `maps.py` لكن المُنفّذ هو Google Places فقط)، فهرس بصمات إدراكية مسبق
الحساب (لقطات المرجع تُلتقط عند الحاجة)، المصادقة متعددة العوامل/الدخول الموحّد، استعادة كلمة المرور، التوسّع على
عدة نسخ، التكامل المستمر، المراقبة.

**الخدمات الخارجية.**

* NextDNS: قائمة المنع حتى 5,000 إدخال، وحدود المعدّل غير منشورة (يتراجع Daggers عند 429)، والهواتف ترى صفحة الحظر
  العادية من NextDNS؛ والتحليلات تعتمد على الخطة.
* صفحة الحكم بعلامة Daggers تحتاج مسار الخادم الخاص، وحتى عندها لا يراها إلا زوار **HTTP العادي**: لا يمكن لأي خادم
  امتلاك شهادة صالحة لنطاق احتيالي، فزيارات HTTPS تحصل على خطأ من المتصفح (ومع ذلك لا يُحمَّل موقع الاحتيال أبداً).
* DNS الخاص في أندرويد يحتاج DoT (المنفذ 853) — غير متاح عادة من استضافة التطبيقات، لذلك NextDNS أو خادم خاص.
* crt.sh وخوادم RDAP و Cert Spotter (حدّ بالساعة دون `CT_API_KEY`) و Serper و DuckDuckGo و Google Places و Gemini و
  Groq كلها لها حصص أو حدود معدّل أو شروط يجب احترامها. اختُبرت NextDNS و AdGuard Home و Serper و Places ونماذج
  اللغة مقابل واجهات وهمية فقط.

**إضافة كروم.** غير منشورة في متجر Chrome الإلكتروني؛ تُحمَّل بوضع المطوّر. قد تغيّر Google بنية صفحة النتائج في أي
وقت فيتعطل وضع الوسوم.

**السجل والتحقق.** تُشحن الإدخالات `pending` ويجب اعتمادها على كل جهاز؛ والاعتماد تنتهي صلاحيته (`max_age_days`).
قد تمنع المواقع الرسمية الجلب الآلي (الشبكة، robots، البنية). المؤسسات الخاصة غير المعتمدة وغير واسعة الاستخدام وغير
الراسخة تحصل على «تحذير». عمر النطاق وحده لا يجعل الموقع آمناً أبداً — يلزم أيضاً HTTPS ونفس الموقع النهائي وعدم
الإدراج في قوائم التهديد وعدم وجود علامات تحذير.

**ضوابط الأمان والخصوصية.** كلمات المرور بـ scrypt، جلسات HttpOnly و SameSite=Strict، حماية CSRF لكل تعديل، أدوار،
قفل بعد محاولات الدخول الفاشلة، سجل تدقيق، CSP وترويسات أمان، وكل استعلامات SQL مُعلَّمة في `backend/app/db/repo.py`. أدلة البلاغات
خالية من البيانات الشخصية (مع التحقق)؛ وتُزال البيانات الشخصية من رسائل الفاحص؛ والإضافة و `/api/scan` لا يخزّنان
شيئاً؛ و DoH وصفحة الحكم لا يسجّلان عناوين IP ولا الأسماء. جلب الصفحات والمصادر الرسمية: Daggers يحلّل DNS بنفسه، وكل
عنوان في كل قفزة إعادة توجيه يجب أن يكون عاماً (تُمنع العناوين الخاصة و loopback و link-local و CGNAT …)، واتصالات
مثبّتة، وإعادة توجيه محدودة. اللقطات لا تملأ النماذج ولا ترسلها وتلغي الطلبات غير GET. لا أسرار في الواجهة ولا في
الإضافة. **`OPEN_ACCESS=1` يلغي تسجيل الدخول للجميع** — للعرض فقط. القائمة الكاملة:
[docs/SECURITY.md](docs/SECURITY.md).

**خطة العمل (لم تبدأ):** المصادقة متعددة العوامل/الدخول الموحّد، مهام الاحتفاظ بالبيانات، Postgres/Redis لعدة نسخ،
خط تكامل مستمر، المراقبة والتنبيه، النشر في متجر Chrome، مصدر سجل رسمي (بدلاً من صفحات عامة تمت مراجعتها)، صفحة
حظر HTTPS بعلامة Daggers عبر مزوّد DNS مُدار.

---

## 7. خريطة الوثائق

| الوثيقة | المحتوى |
|---|---|
| [docs/API.md](docs/API.md) | عقد الواجهة البرمجية وحقول الحكم |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | البنية ومسارات البيانات وقاعدة البيانات |
| [docs/CHECKER.md](docs/CHECKER.md) · [docs/CHECKER-ACCURACY.md](docs/CHECKER-ACCURACY.md) | الفاحص المباشر وفحوص دقته |
| [docs/GOVERNMENT-SAFE.md](docs/GOVERNMENT-SAFE.md) | توثيق الجهات الحكومية وسياسة «آمن» |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/RUNBOOK.md](docs/RUNBOOK.md) | التثبيت والإنتاج والتشغيل |
| [docs/SECURITY.md](docs/SECURITY.md) | ضوابط الأمان وحدودها |
| [docs/TESTING-REPORT.md](docs/TESTING-REPORT.md) | ما تم اختباره وما لم يُختبر |
| [docs/INTEGRATION-REPORT.md](docs/INTEGRATION-REPORT.md) | كيف دُمجت مسارات العمل WS1/WS2/WS3 |
| [docs/WS2.md](docs/WS2.md) · [docs/WS2-README.md](docs/WS2-README.md) | سياسة الثقة والسجل والقنوات والحارس |
| [docs/UI-KIT.md](docs/UI-KIT.md) | نظام التصميم |
| [guard/README.md](guard/README.md) · [extension/README.md](extension/README.md) | مسارا الحارس A/B · إضافة كروم |

</div>
