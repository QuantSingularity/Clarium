# Clarium

## RegTech Compliance Module

> **Standalone compliance infrastructure for the Abrar Ahmed Fintech Suite.**
> KYC pipeline, AML transaction monitoring, immutable audit trail,
> jurisdiction rule engine, webhook notifications, and a React admin dashboard.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Clarium Compliance Platform                   │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ KYC Pipeline│  │  AML Engine │  │  Jurisdiction Rules      │  │
│  │             │  │             │  │                          │  │
│  │ Doc upload  │  │ Amount check│  │  YAML per country        │  │
│  │ Mock OCR    │  │ Velocity    │  │  Limits / Disclosures    │  │
│  │ ID scoring  │  │ Geo risk    │  │  Age gates / KYC tiers   │  │
│  │State machine│  │ PEP match   │  │  Hot-reload via API      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────────────────────┘  │
│         │                │                                       │
│  ┌──────▼────────────────▼──────────────────────────────────┐    │
│  │              Audit Trail (hash-chained)                  │    │
│  │   SHA-256 prev_hash → this_hash chain  ·  tamper-proof   │    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐    │
│  │           Webhook Delivery (HMAC-signed, retry)          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  FastAPI :8000  ·  PostgreSQL  ·  Redis  ·  React Admin :3000    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker ≥ 24 + Docker Compose v2

### 1. Configure

```bash
git clone https://github.com/abrar/clarium.git
cd clarium
cp .env.example .env
# Defaults work out of the box
```

### 2. Start

```bash
make up
# or: docker compose up -d --build
```

| Service            | URL                        |
| ------------------ | -------------------------- |
| API (Swagger docs) | http://localhost:8000/docs |
| Admin dashboard    | http://localhost:3000      |
| PostgreSQL         | localhost:5432             |
| Redis              | localhost:6379             |

### 3. Try the API

```bash
# Submit KYC
curl -X POST http://localhost:8000/kyc/submit \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "full_name": "Alice Johnson",
    "date_of_birth": "1990-05-15",
    "nationality": "US",
    "document_type": "passport",
    "document_number": "A12345678"
  }'

# Upload document (triggers OCR + scoring)
curl -X POST http://localhost:8000/kyc/upload/user_001 \
  -F "file=@/path/to/passport.jpg"

# Check status
curl http://localhost:8000/kyc/status/user_001

# Run AML check
curl -X POST http://localhost:8000/aml/check \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_001",
    "user_id": "user_001",
    "amount": 15000,
    "currency": "USD",
    "source_country": "US",
    "destination_country": "RU"
  }'

# Get audit trail
curl http://localhost:8000/audit/trail/user_001

# Get jurisdiction rules
curl http://localhost:8000/rules/US
```

---

## API Reference

### KYC Pipeline

| Method  | Endpoint                | Description                                        |
| ------- | ----------------------- | -------------------------------------------------- |
| `POST`  | `/kyc/submit`           | Submit KYC application                             |
| `POST`  | `/kyc/upload/{user_id}` | Upload identity document (triggers OCR + scoring)  |
| `GET`   | `/kyc/status/{user_id}` | Get KYC status and score                           |
| `PATCH` | `/kyc/review/{user_id}` | Admin: override KYC decision                       |
| `GET`   | `/kyc/queue`            | Admin: list all submissions (filterable by status) |

**KYC State Machine:**

```
pending → processing → verified
                    → rejected
                    → review → verified
                             → rejected
```

**Identity Scoring (0-1):**

- OCR confidence - 40%
- Name match - 30%
- Document number match - 20%
- Age check (18+) - 10%

Score ≥ 0.75 → `verified` · Score 0.50-0.74 → `review` · Score < 0.50 → `rejected`

### AML Transaction Monitoring

| Method  | Endpoint           | Description                    |
| ------- | ------------------ | ------------------------------ |
| `POST`  | `/aml/check`       | Run AML check on a transaction |
| `GET`   | `/aml/flags`       | List flagged transactions      |
| `GET`   | `/aml/flags/{id}`  | Get AML check detail           |
| `PATCH` | `/aml/review/{id}` | Update case status             |

**Four AML Rules:**

| Rule             | Trigger                           | Risk Weight |
| ---------------- | --------------------------------- | ----------- |
| Amount threshold | Single txn ≥ $10,000              | +0.40       |
| Velocity         | ≥ 10 txns in 60 min per user      | +0.35       |
| Geographic risk  | Source/dest country score ≥ 0.70  | up to +0.20 |
| PEP matching     | User ID fuzzy-matched in PEP list | +0.50       |

Overall risk ≥ 0.70 or any flag triggered → transaction flagged.

### Audit Trail

| Method | Endpoint                   | Description                                    |
| ------ | -------------------------- | ---------------------------------------------- |
| `GET`  | `/audit/trail/{entity_id}` | Full audit history for an entity               |
| `GET`  | `/audit/recent`            | Latest audit events across all entities        |
| `GET`  | `/audit/verify`            | Verify hash-chain integrity (tamper detection) |

**Hash chaining:** Every event stores `SHA-256(content + prev_hash)`. Changing any historical record breaks the chain of every subsequent event, making tampering detectable.

### Jurisdiction Rules

| Method | Endpoint                   | Description                                   |
| ------ | -------------------------- | --------------------------------------------- |
| `GET`  | `/rules/`                  | List all loaded jurisdiction codes            |
| `GET`  | `/rules/{code}`            | Full rule set for a jurisdiction              |
| `POST` | `/rules/check/transaction` | Check transaction against jurisdiction limits |
| `POST` | `/rules/check/age`         | Check age gate for jurisdiction               |
| `POST` | `/rules/reload`            | Hot-reload rules from YAML files              |

**Loaded jurisdictions:** US · GB · EU · SG · AE

**Add your own:** Create `rules/jurisdictions/XX.yaml` and call `POST /rules/reload`.

### Webhooks

| Method   | Endpoint                    | Description                 |
| -------- | --------------------------- | --------------------------- |
| `POST`   | `/webhooks/`                | Register a webhook endpoint |
| `GET`    | `/webhooks/`                | List registered webhooks    |
| `DELETE` | `/webhooks/{id}`            | Remove a webhook            |
| `GET`    | `/webhooks/{id}/deliveries` | View delivery history       |

**Available events:** `kyc.submitted` · `kyc.verified` · `kyc.rejected` · `kyc.review` · `aml.flagged` · `aml.cleared` · or `*` for all.

**HMAC signing:** Each delivery includes `X-Clarium-Signature: sha256=<hmac>` when a secret is set. Verify on your server:

```python
import hmac, hashlib, json

def verify(secret: str, payload: dict, signature: str) -> bool:
    body = json.dumps(payload, sort_keys=True).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

**Retry policy:** Up to 3 attempts with exponential backoff (30s, 60s, 90s).

### Admin

| Method   | Endpoint          | Description              |
| -------- | ----------------- | ------------------------ |
| `GET`    | `/admin/stats`    | Dashboard summary counts |
| `GET`    | `/admin/pep/list` | View PEP list            |
| `POST`   | `/admin/pep`      | Add PEP entry            |
| `DELETE` | `/admin/pep/{id}` | Remove PEP entry         |

---

## Jurisdiction Rule YAML Format

```yaml
# rules/jurisdictions/MY.yaml
jurisdiction: MY
effective_date: "2024-01-01"
authority: "BNM (Bank Negara Malaysia)"

transaction_limits:
  max_single_transaction: 200000 # MYR
  cash_reporting_threshold: 50000 # MYR

age_gate:
  minimum_age: 18

kyc_tiers:
  - level: basic
    threshold: 0
    requirements: [name_verification, ic_or_passport]
  - level: enhanced
    threshold: 50000
    requirements: [name_verification, ic_or_passport, source_of_funds]

required_disclosures:
  - "Regulated by Bank Negara Malaysia under AMLATFPUAA 2001."

aml_rules:
  sar_threshold: 25000
  structuring_detection: true

geographic_restrictions:
  blocked_countries: [KP, IR]
```

Then call `POST /rules/reload` - no restart required.

---

## Rate Limiting

Redis-based sliding-window rate limiting per IP:

| Route              | Limit         |
| ------------------ | ------------- |
| `POST /kyc/submit` | 10 req / 60s  |
| `POST /kyc/upload` | 5 req / 60s   |
| `POST /aml/check`  | 100 req / 60s |
| All others         | 200 req / 60s |

Returns `HTTP 429` with `retry_after` seconds when exceeded.

---

## Admin Dashboard

React SPA at `http://localhost:3000` with five sections:

| Page          | Features                                                                                        |
| ------------- | ----------------------------------------------------------------------------------------------- |
| **Dashboard** | KYC counts by status (chart), AML totals, PEP matches, audit event rate                         |
| **KYC Queue** | Filterable table, click any row to open review panel, submit verified/rejected/review decisions |
| **AML Flags** | Flagged transactions with risk score, flag reasons, PEP badge, one-click status updates         |
| **Audit Log** | Search by entity ID, recent events, hash-chain integrity verification button                    |
| **Webhooks**  | Register/delete endpoints, select event subscriptions, HMAC secret config                       |
| **Rules**     | Browse jurisdiction rules - transaction limits, KYC tiers, disclosures, hot-reload              |

---

## Running Tests

```bash
make test
# or manually:
cd backend
pip install -r requirements.txt aiosqlite
pytest tests/ -v
```

**Test coverage:**

- `test_kyc.py` - 7 tests: submit, duplicate, status, queue, invalid doc type, underage scoring
- `test_aml.py` - 7 tests: clear transaction, amount threshold, geo risk, list flags, invalid amount, direct rule engine
- `test_audit.py` - 8 tests: event creation, hash presence, chain validity, chaining, determinism, filter
- `test_webhooks_rules.py` - 11 tests: register, list, delete, signing, queue, jurisdiction CRUD, tx check, age check, KYC tiers

---

## Folder Structure

```
clarium/
├── Makefile
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── src/
│   │   ├── main.py              # FastAPI app + middleware wiring
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models/              # ORM: KYC, AML, Audit, Webhook, PEP
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── kyc.py           # submit, upload, status, review, queue
│   │   │   ├── aml.py           # check, flags, review
│   │   │   ├── audit.py         # trail, verify, recent
│   │   │   ├── webhooks.py      # register, list, delete, deliveries
│   │   │   ├── rules.py         # list, get, check, reload
│   │   │   └── admin.py         # stats, pep list/add/remove
│   │   ├── services/
│   │   │   ├── kyc_service.py   # Mock OCR, identity scoring, state machine
│   │   │   ├── aml_service.py   # 4 AML rules: amount, velocity, geo, PEP
│   │   │   ├── audit_service.py # SHA-256 hash-chained event log
│   │   │   ├── rule_engine.py   # YAML jurisdiction loader + enforcement
│   │   │   └── webhook_service.py # HMAC signing, queuing, delivery
│   │   ├── middleware/
│   │   │   ├── rate_limit.py    # Redis sliding-window per IP
│   │   │   └── jurisdiction.py  # X-Jurisdiction header enforcement
│   │   └── workers/
│   │       └── webhook_worker.py # Background delivery with retries
│   └── tests/
│       ├── conftest.py          # SQLite in-memory fixtures
│       ├── test_kyc.py
│       ├── test_aml.py
│       ├── test_audit.py
│       └── test_webhooks_rules.py
│
├── frontend/
│   ├── Dockerfile               # Multi-stage: Vite build → nginx
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # React Router wiring
│       ├── api/index.js         # Axios client for all endpoints
│       ├── components/
│       │   ├── UI.jsx           # Badge, Card, Table, Button, Input, Spinner
│       │   └── Layout.jsx       # Sidebar navigation
│       └── pages/
│           ├── Dashboard.jsx    # Stats + KYC chart
│           ├── KYCPage.jsx      # Queue + review modal
│           ├── AMLPage.jsx      # Flags table + detail panel
│           ├── AuditPage.jsx    # Event log + chain verification
│           ├── WebhooksPage.jsx # Register/manage webhooks
│           └── RulesPage.jsx    # Jurisdiction browser
│
├── rules/
│   └── jurisdictions/
│       ├── US.yaml
│       ├── GB.yaml
│       ├── EU.yaml
│       ├── SG.yaml
│       └── AE.yaml
│
└── infra/
    └── postgres/
        └── init.sql             # Schema + seed PEP data
```

---

## Connecting to Other Suite Services

**From Flowlet (1) or PayNext (2):**

```python
import httpx

CLARIUM_URL = "http://clarium-api:8000"

# KYC check before onboarding
async def verify_user(user_id: str, doc_data: dict) -> dict:
    async with httpx.AsyncClient() as c:
        await c.post(f"{CLARIUM_URL}/kyc/submit", json={**doc_data, "user_id": user_id})
        r = await c.get(f"{CLARIUM_URL}/kyc/status/{user_id}")
        return r.json()

# AML check before processing payment
async def screen_transaction(txn: dict) -> bool:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{CLARIUM_URL}/aml/check", json=txn)
        result = r.json()
        return not result["flagged"]
```

**Register webhook for real-time KYC notifications:**

```bash
curl -X POST http://localhost:8000/webhooks/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://flowlet-api:8001/hooks/kyc",
    "secret": "shared-hmac-secret",
    "events": ["kyc.verified", "kyc.rejected"]
  }'
```

---
