# Landloads — Landlord Management Platform Design

**Date:** 2026-05-08
**Status:** Draft for review
**Author:** Initial design via Claude Code brainstorming session

## 1. Purpose & Scope

Landloads is a web platform that helps a Kenyan landlord (single-landlord MVP) manage their properties, onboard tenants, collect rent via M-Pesa, and handle delayed payments through automated reminders, late-fee accrual, and tenant-requested payment plans.

### 1.1 MVP scope (this spec)

In scope:

1. Properties & units management
2. Tenant onboarding (invite → KYC → lease assignment → e-sign acknowledgment)
3. Rent collection via M-Pesa STK Push and C2B Paybill webhook
4. Delayed-payment workflow: scheduled reminders, configurable late-fee accrual, payment-plan request/approval
5. Receipts & per-tenant ledger
6. Landlord dashboard with occupancy, collection, and defaulter visibility
7. Tenant portal for payment, history, lease access, and plan requests

### 1.2 Out of scope (Phase 2, documented in §11)

Maintenance requests, lease renewal automation, vacancy listings, multi-landlord SaaS mode, expense tracking, credit scoring, WhatsApp, native mobile apps, ML rent-default prediction.

### 1.3 Non-goals

- Multi-tenant SaaS architecture in MVP (single-landlord deployment per instance)
- Native mobile apps (responsive web only)
- Languages other than English (i18n keys structured for Swahili later)

## 2. Architecture

### 2.1 System diagram

```
                            ┌─────────────────────┐
                            │   Nginx (reverse    │
                            │   proxy + TLS)      │
                            └──────────┬──────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
       ┌────────▼─────────┐  ┌─────────▼────────┐    ┌────────▼─────────┐
       │  Next.js 15 SSR  │  │  FastAPI         │    │  Static assets   │
       │  (frontend)      │◄─┤  (backend API)   │    │  /uploads etc.   │
       │  Docker          │  │  Docker          │    └──────────────────┘
       └──────────────────┘  └────┬─────┬───┬───┘
                                  │     │   │
                ┌─────────────────┘     │   └─────────────────┐
                │                       │                     │
       ┌────────▼─────────┐  ┌──────────▼─────────┐  ┌────────▼─────────┐
       │  PostgreSQL 16   │  │  Redis             │  │  MinIO           │
       │  (primary DB)    │  │  (cache, queue,    │  │  (S3-compatible  │
       │  Docker volume   │  │   rate limiting)   │  │   KYC/receipts)  │
       └──────────────────┘  └──────────┬─────────┘  └──────────────────┘
                                        │
                              ┌─────────▼──────────┐
                              │  arq worker        │
                              │  (background jobs) │
                              │  Docker            │
                              └────────────────────┘

External integrations (called from FastAPI):
  • Safaricom Daraja API  — STK Push, C2B Paybill webhook, STK Query
  • Africa's Talking      — SMS
  • SMTP / Resend         — email
```

### 2.2 Tech stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui + Framer Motion | Interactive UI; SSR for tenant portal speed on slow networks |
| Backend | FastAPI (Python 3.12) + Pydantic v2 | Async-native, ideal for Daraja webhooks, OpenAPI generated for frontend client |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Mature, typed; Alembic owns schema |
| Auth | FastAPI-Users with JWT (access + refresh) in httpOnly cookies; SMS OTP for tenant first-time invite acceptance | Off-the-shelf, supports our flows; cookie auth simpler than Bearer for SSR frontend |
| Background jobs | arq (Redis-backed, asyncio-native) | Simpler than Celery; durable retries for Daraja calls |
| DB | PostgreSQL 16 in Docker, named volume | Self-hosted per requirement |
| Cache & queue | Redis 7 in Docker | Sessions, rate limits, arq queue |
| File storage | MinIO in Docker (S3-compatible) | KYC docs, receipt PDFs; clean backup story |
| Reverse proxy | Nginx + Certbot | TLS termination, single ingress |
| PDF | WeasyPrint | Receipts, statements |
| Observability | Sentry, structured JSON logs to stdout | Lightweight; Loki/Grafana addable later |

### 2.3 Deployment

- One `docker-compose.yml` orchestrating: `frontend`, `backend`, `worker`, `postgres`, `redis`, `minio`, `nginx`
- Configuration via `.env`; production secrets via Docker secrets
- Daraja requires whitelisting our public IP / domain
- Nightly `pg_dump` → MinIO bucket, retention 14 days; weekly restore drill in staging

## 3. Data Model

### 3.1 Entities

```
User                Auth principal; role ∈ {landlord, tenant, admin}
  id, phone, email, name, role, kraPin, idNumber (encrypted),
  passwordHash, createdAt, updatedAt

Property            A building or compound owned by the landlord
  id, landlordId→User, name, address, lat, lng, photoUrl

Unit                A rentable space inside a property
  id, propertyId, label, bedrooms, rentAmount, depositAmount,
  dueDayOfMonth, status ∈ {vacant, occupied}

Tenant              KYC-completed person who can sign leases
  id, userId→User, idDocUrl, employer, nextOfKin (jsonb),
  kycStatus ∈ {pending, approved, rejected}

Lease               Tenancy agreement
  id, unitId, tenantId, startDate, endDate, rentAmount,
  depositAmount,
  lateFeeRule (jsonb: {
    type: "flat" | "percent",
    value: number,        # KES if flat, % of rent if percent
    cadence: "once" | "daily" | "monthly",
    graceDays: number,    # days past due before accrual starts
    capMonths: number     # max accrual capped at N months of rent
  }),
  status ∈ {active, ended, terminated}

Invoice             Rent obligation for one billing period
  id, leaseId, periodStart, periodEnd, dueDate, amount,
  lateFeeAccrued, status ∈ {open, partial, paid, overdue, on_pay_plan,
  defaulted, written_off}

Payment             Money received
  id, invoiceId (nullable for unmatched), tenantId, amount,
  channel ∈ {mpesa_stk, mpesa_c2b, cash, bank},
  mpesaReceipt (nullable), checkoutRequestId (nullable),
  rawCallback (jsonb), status ∈ {pending, success, failed, reversed},
  createdAt

PaymentPlan         Tenant-proposed deferred schedule
  id, invoiceId, requestedAt, approvedBy (nullable),
  schedule (jsonb: [{date, amount, paidPaymentId}]),
  status ∈ {pending, approved, rejected, completed, defaulted}

NotificationLog     Every SMS/email — audit + delivery trail
  id, recipientUserId, channel ∈ {sms, email}, template, body,
  providerMessageId, status ∈ {queued, sent, delivered, failed}, sentAt

AuditEvent          Append-only log of admin actions
  id, actorId, action, entityType, entityId, meta (jsonb), at
```

### 3.2 Key invariants

- `Payment` is idempotent on `(channel, mpesaReceipt)` via unique partial index where `mpesaReceipt IS NOT NULL`.
- Also idempotent on `checkoutRequestId` for STK Push callbacks (unique partial index).
- `Invoice.status` is computed from sum of successful `Payment` rows + plan state — not directly mutated by user input.
- Postgres `audit_event` table: app role has only `INSERT, SELECT`; `UPDATE` and `DELETE` revoked.
- Row-level access enforced in SQLAlchemy queries: tenant sees own rows, landlord sees own properties' rows.

### 3.3 Encryption & PII

- `User.idNumber` and `User.kraPin` encrypted using `pgcrypto` with key from env
- KYC documents stored in MinIO; access only via short-lived (5 min) signed URLs
- Password hashing: argon2 (FastAPI-Users default)

## 4. Key Flows

### 4.1 M-Pesa STK Push (tenant-initiated)

1. Tenant opens `/tenant/pay`, confirms amount and phone
2. Frontend → `POST /api/payments/stk` with `{leaseId, amount}`
3. Backend: lock open invoice (`SELECT FOR UPDATE`), insert `Payment(status=pending, checkoutRequestId)`, call Daraja STK Push
4. Daraja prompts tenant phone; tenant enters PIN
5. Daraja calls webhook `POST /api/mpesa/stk-callback`
6. Backend webhook handler:
   - Verify Daraja IP via Nginx allowlist; verify path token (callback URL is `/api/mpesa/stk-callback/{DARAJA_CALLBACK_SECRET}`, the secret is a 32-byte random token compared in constant time)
   - Dedupe by `checkoutRequestId` (insert-or-skip)
   - On success: update `Payment.status=success`, `mpesaReceipt`; recompute invoice status; enqueue receipt PDF + SMS confirmation jobs
   - On failure: update `Payment.status=failed`, store reason
7. Frontend polls `GET /api/payments/:id` (or SSE) until terminal state; shows animated receipt on success

**Stuck-payment recovery:** hourly arq job queries Daraja STK Query API for `Payment(status=pending, createdAt < now - 5min)` and reconciles.

### 4.2 M-Pesa C2B Paybill (out-of-app)

1. Tenant pays Paybill from M-Pesa menu, account ref = tenant code
2. Daraja calls webhook `POST /api/mpesa/c2b`
3. Backend matches by `accountReference`:
   - Match → apply to oldest open invoice; auto-receipt SMS
   - Partial match → flag for landlord review
   - No match → park as `Payment(invoiceId=null)` in unmatched queue; landlord allocates manually in admin

### 4.3 Daily reminder & late-fee job (arq cron @ 06:00 EAT)

- Generate invoices for leases entering new period (1st of month or `Unit.dueDayOfMonth`)
- Send T-3 SMS reminders for invoices due in 3 days
- Send T-0 reminders for invoices due today
- Mark unpaid past-due invoices as `overdue` after `lateFeeRule.graceDays`
- Accrue late fees on `overdue` invoices per rule (flat or percent, optionally daily); cap at `capMonths` of rent
- Send escalation SMS at T+3, T+7, T+14

### 4.4 Invoice state machine

```
   ┌─────────┐  past due+grace   ┌─────────┐
   │  open   ├──────────────────►│ overdue │
   └────┬────┘                   └────┬────┘
        │ partial pay                 │ partial pay
        ▼                             ▼
   ┌──────────┐  past due+grace  ┌──────────┐
   │ partial  ├─────────────────►│ partial* │   (* still partial, but past due — eligible for plan)
   └────┬─────┘                  └────┬─────┘
        │ full pay                    │ plan approved (overdue OR partial-past-due)
        ▼                             ▼
   ┌─────────┐                ┌──────────────┐
   │  paid   │                │ on_pay_plan  │
   └─────────┘                └──────┬───────┘
                                     │
                installment missed   │   all installments paid
                       ┌─────────────┴─────────────┐
                       ▼                           ▼
                 ┌──────────┐                ┌─────────┐
                 │defaulted │                │  paid   │
                 └──────────┘                └─────────┘

   `written_off`: terminal state set only by landlord admin action; not part of normal flow.
```

Illegal transitions raise `IllegalStateError` and are rejected by the service layer.

### 4.5 Payment plan request

**Eligibility:** Only invoices in `overdue` or `partial` (when past `dueDate`) status can have a plan requested. The tenant UI hides the request action for other states.

1. Tenant on an eligible invoice screen submits proposed schedule
2. Backend: insert `PaymentPlan(status=pending)`; notify landlord (SMS + email + dashboard alert)
3. Landlord approves / rejects / counter-proposes in admin
4. On approve:
   - Invoice status → `on_pay_plan`
   - Late-fee accrual suspended (cron skips invoices in this state)
   - Tenant pays each installment via STK Push, payments linked to schedule entries
5. On installment missed by 24h: plan → `defaulted`, invoice → `defaulted`, late-fee accrual resumes, landlord notified

### 4.6 Critical edge cases (designed in, not bolted on)

| Risk | Mitigation |
|---|---|
| Duplicate Daraja callbacks (they retry) | Unique partial index on `(channel, mpesaReceipt)` and `checkoutRequestId` |
| STK callback never arrives | Hourly STK Query reconciliation job |
| Tenant pays wrong (small) amount | Allow partial; track outstanding; do not auto-reject |
| Tenant overpays | Credit ledger entry on tenant; auto-applied to next invoice |
| Daraja reversal | Admin action creates negative `Payment`, reopens invoice, audit event |
| Webhook spoofing | Nginx IP allowlist + secret token in callback URL path |
| Tenant phone number changes | Phone is contact info, not identity — `User.id` is identity |
| Late-fee runaway on long-dormant invoices | `lateFeeRule.capMonths` enforced at accrual time |
| Race: two callbacks for same payment | DB transaction with `SELECT ... FOR UPDATE` on invoice row |
| Daraja sandbox vs prod env mix-up | Env-specific config; integration tests run against sandbox only |

## 5. UI Structure

### 5.1 Landlord admin (`/dashboard/*`)

| Route | Purpose |
|---|---|
| `/dashboard` | Overview: occupancy, collected, outstanding, defaulter list, trend chart |
| `/dashboard/properties` | Grid of properties |
| `/dashboard/properties/:id` | Building detail, units, occupancy, photos |
| `/dashboard/units/:id` | Unit detail, lease history, current tenant |
| `/dashboard/tenants` | Searchable list with KYC status badges |
| `/dashboard/tenants/:id` | Profile, KYC, lease, ledger, audit trail |
| `/dashboard/leases` | Active/ended leases, filters |
| `/dashboard/leases/new` | Wizard: unit → tenant → terms → e-sign acknowledgment |
| `/dashboard/leases/:id` | Lease detail, late-fee rule, end/renew |
| `/dashboard/invoices` | Filterable; bulk reminder send |
| `/dashboard/payments` | All payments; unmatched queue surfaced at top |
| `/dashboard/payments/unmatched` | Manual allocation UI for typo'd paybill refs |
| `/dashboard/plans` | Plan requests: pending review, active, defaulted |
| `/dashboard/notifications` | SMS/email log + delivery status |
| `/dashboard/settings/mpesa` | Daraja keys, paybill, callback URL test |
| `/dashboard/settings/reminders` | Reminder cadence templates |
| `/dashboard/settings/late-fees` | Default lease rule (overridable per-lease) |
| `/dashboard/settings/profile` | Landlord profile, KRA PIN, business info |

### 5.2 Tenant portal (`/tenant/*`)

| Route | Purpose |
|---|---|
| `/tenant` | Home: due-amount card, [Pay Now], recent activity, plan status |
| `/tenant/pay` | STK initiator with live status |
| `/tenant/history` | Payment history; downloadable statements |
| `/tenant/lease` | Read-only lease document, landlord contact |
| `/tenant/plan` | Request plan (overdue only); active plan view |
| `/tenant/profile` | KYC, next of kin, employment, change password |
| `/tenant/notifications` | Inbox |

### 5.3 Auth (`/auth/*`)

| Route | Purpose |
|---|---|
| `/auth/login` | Email/phone + password |
| `/auth/landlord/register` | Landlord self-signup |
| `/auth/tenant/accept/:token` | Invite link → SMS OTP → password → KYC |
| `/auth/forgot` | Email or SMS recovery |

### 5.4 Design language

- shadcn/ui base; customize tokens, do not fork components
- Framer Motion for page transitions, STK status pulse, receipt reveal
- Mobile-first; admin tested on tablet + desktop
- Money formatting: `KES 25,000` via `Intl.NumberFormat('en-KE')`, no decimals on whole shillings
- Empty states with CTAs everywhere — no blank screens
- Color cues: green=paid, amber=due-soon, red=overdue (avoid pure red on small text)
- Optimistic UI + skeletons (not spinners) on data loads
- Toast + inline errors — never silent failures

## 6. Module Boundaries (Backend)

```
app/
├── core/             # config, security, logging, db session
├── auth/             # FastAPI-Users routes + custom OTP flow
├── users/            # User model, profile, RBAC checks
├── properties/       # Property + Unit
├── tenants/          # Tenant model, KYC workflow
├── leases/           # Lease lifecycle, late-fee rule encoding
├── invoices/         # Invoice generation, state machine, queries
├── payments/         # Payment model, STK initiate, reconciliation
├── plans/            # PaymentPlan request/approval/installment tracking
├── mpesa/            # Daraja client, STK Push, C2B handler, STK Query
├── notifications/    # SMS/email senders, templates, log
├── audit/            # AuditEvent helpers
├── jobs/             # arq tasks (reminders, late-fee accrual, reconciliation, STK query, PDF gen)
└── api/              # FastAPI routers wiring services to HTTP
```

Each module exposes a service layer (pure functions / class methods) that the API routers call. Service layer is tested in isolation with a real Postgres via testcontainers.

## 7. Testing Strategy

| Layer | Tool | Scope |
|---|---|---|
| Backend unit | pytest, pytest-asyncio | Pure functions: late-fee calc, invoice state, plan scheduling |
| Backend integration | pytest + testcontainers-postgres | Real Postgres, migrations applied, SQLAlchemy queries |
| Daraja mocking | respx (httpx mock) | STK request, callback handling, edge cases including duplicates |
| Daraja sandbox | Daraja sandbox env in staging | End-to-end smoke before each prod deploy |
| Frontend unit | Vitest + React Testing Library | Components, hooks, formatters |
| Frontend e2e | Playwright | Critical flows: tenant pays rent, landlord onboards tenant, plan approval |
| Contract | Pydantic schemas + OpenAPI client gen | Frontend types stay in sync with backend |

**Discipline:**

- Integration tests must hit a real Postgres (testcontainers), never a mock — payment logic is too risky to mock the DB
- Every webhook handler has an explicit duplicate-callback test
- Every state transition has a test for illegal transitions (must reject)
- Every late-fee rule shape has a deterministic test fixture

## 8. Non-Functional Requirements

| Concern | Target / Decision |
|---|---|
| Performance | Dashboard < 1s for landlord with 100 units; STK initiation < 2s p95 |
| Security | OWASP top 10 review; rate limit `/auth/*` and `/payments/stk` (Redis); CSRF on cookie auth; argon2 hashing |
| PII | `idNumber`, `kraPin` encrypted at rest (pgcrypto); KYC docs in MinIO with 5-min signed URLs |
| Webhook auth | Daraja IP allowlist at Nginx + secret token in callback path |
| Audit immutability | `audit_event` append-only via Postgres role grants |
| Backups | Nightly `pg_dump` → MinIO; weekly restore drill in staging |
| Observability | Sentry (errors), structured JSON logs, `/healthz` + `/readyz`, request-ID propagation |
| Accessibility | WCAG AA on tenant portal critical flows |
| i18n | English only for MVP; copy via `next-intl` keys to enable Swahili later |
| Compliance | Kenya Data Protection Act 2019: privacy notice on signup, data export endpoint, deletion on lease close + 7-year retention for tax |

## 9. Configuration & Secrets

Environment variables (`.env` for dev, Docker secrets for prod):

```
# Database
DATABASE_URL=postgresql+asyncpg://landloads:***@postgres:5432/landloads

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=landloads

# Auth
JWT_SECRET=...
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30
PII_ENCRYPTION_KEY=...

# Daraja (Safaricom)
DARAJA_ENV=sandbox|production
DARAJA_CONSUMER_KEY=...
DARAJA_CONSUMER_SECRET=...
DARAJA_SHORTCODE=...
DARAJA_PASSKEY=...
DARAJA_CALLBACK_SECRET=...   # path token for callback verification

# SMS
AT_USERNAME=...
AT_API_KEY=...
AT_SENDER_ID=...

# Email
RESEND_API_KEY=...
EMAIL_FROM=no-reply@example.co.ke

# Observability
SENTRY_DSN=...
LOG_LEVEL=INFO
```

## 10. Open Questions

These do not block writing the implementation plan but should be answered before launch:

1. Domain name and hosting provider (affects Daraja IP whitelisting)
2. Daraja paybill number — own paybill or aggregator (e.g., Lipa Na Mpesa Online)
3. Receipt branding (landlord logo, business name, KRA PIN on receipt)
4. SMS sender ID registration (Africa's Talking; takes ~3-5 business days)
5. Whether landlord wants a soft-reminder channel (email) in addition to SMS for cost reasons

## 11. Phase 2 (Documented, Not Built)

| Feature | Notes |
|---|---|
| Maintenance requests | Tenant submits with photos; landlord assigns/closes; status workflow |
| Lease renewal automation | Auto-generate renewal 60 days before end; tenant accept/decline |
| Vacancy listings | Public listing pages; applicant inquiries; basic screening |
| Multi-landlord SaaS mode | Organization tier, RBAC, per-org M-Pesa creds, billing model |
| Expense tracking | Per-property expenses, P&L, tax-time export |
| Tenant credit scoring | Score from on-time payment history, shareable with other landlords |
| WhatsApp notifications | Meta Cloud API; replaces or supplements SMS |
| Native mobile apps | React Native sharing API client with web frontend |
| ML rent-default prediction | Trained on payment history + tenant profile |

## 12. Build Order (preview, formalized in implementation plan)

The implementation plan (next step) will sequence:

1. Repo + Docker Compose scaffold + CI
2. Database schema + Alembic baseline
3. Auth (landlord signup, login, tenant invite + OTP)
4. Properties + Units CRUD
5. Tenants + KYC upload
6. Leases + invoice generation cron
7. M-Pesa STK Push (sandbox first)
8. M-Pesa C2B + unmatched queue
9. Reminders + late-fee accrual
10. Payment plans
11. Receipts (PDF) + statements
12. Landlord dashboard
13. Tenant portal
14. Production deploy + Daraja go-live
