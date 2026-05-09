# Production cutover runbook

This is the gate from `v0.16.0-tenant-portal` → `v1.0.0`. The box says
green only when every step below has been executed and signed off
(initial + date in `docs/runbooks/cutover-history.md`).

## 0. Pre-flight (T-7 days)

- [ ] Domain provisioned (`landloads.example.co.ke`) — A record points
      at production server.
- [ ] Africa's Talking sender ID registered (3-5 day lead time per
      design §10 Q4).
- [ ] Daraja production app credentials provisioned and stored in 1Password.
- [ ] Sentry project created; DSN noted.

## 1. Server bootstrap (T-3 days)

- [ ] Docker + docker-compose v2 installed.
- [ ] `git clone` Landloads to `/opt/landloads`.
- [ ] Copy `.env.production.example` → `/opt/landloads/.env`; fill in
      every `CHANGE_ME` slot. Verify with:
      ```bash
      grep CHANGE_ME /opt/landloads/.env  # must print nothing
      ```
- [ ] `docker compose up -d postgres redis minio` — wait for healthy.
- [ ] Run migrations from a one-off container:
      ```bash
      docker compose run --rm backend alembic upgrade head
      ```
- [ ] Verify the partial unique indexes:
      ```sql
      SELECT indexname FROM pg_indexes
      WHERE tablename IN ('payments','leases')
      AND indexname LIKE 'uq_%';
      ```

## 2. TLS + Nginx hardening (T-2 days)

- [ ] Follow [docs/runbooks/tls.md](./tls.md) to install Certbot.
- [ ] Swap `default.conf` → `default.prod.conf`.
- [ ] `nginx -t && systemctl reload nginx`.
- [ ] `curl -sSI https://landloads.example.co.ke/healthz` returns
      `200` with HSTS header.

## 3. M-Pesa cutover (T-1 day)

- [ ] In `.env`: `MPESA_ENV=production`, real consumer key/secret,
      real paybill, fresh `MPESA_CALLBACK_SECRET` (32 random chars).
- [ ] Verify the Daraja allowlist is enabled in Nginx
      (`/api/webhooks/mpesa/` returns 403 from a non-Daraja IP).
- [ ] Restart backend + worker:
      ```bash
      docker compose up -d --force-recreate backend worker
      ```

## 4. Backups (T-1 day)

- [ ] `crontab -e`:
      ```
      0 2 * * * cd /opt/landloads && ./deploy/backup/backup.sh \
          >> /var/log/landloads-backup.log 2>&1
      ```
- [ ] Run it once manually to confirm an upload to `s3://landloads-backups/daily/`.
- [ ] Execute the [restore drill](./restore.md) on a staging Postgres.
      Record the result in `restore-history.md`.

## 5. Compliance + observability

- [ ] Sentry receives events: trigger an artificial 500 on a staging
      route, watch it land.
- [ ] Privacy notice reachable at `https://landloads.example.co.ke/privacy`.
- [ ] `GET /api/me/export` returns a JSON download for the operator's
      account.

## 6. Real-shilling smoke test (T-0)

- [ ] From a real M-Pesa account, run a 1 KES STK Push:
      tenant phone → STK prompt → success → invoice flips
      to `paid` → SMS receipt landed → PDF receipt downloadable.
- [ ] From the same account, send a 1 KES C2B Paybill payment with
      a valid tenant code → matched automatically.
- [ ] Repeat with an intentionally-wrong tenant code → lands in the
      unmatched queue → landlord allocates manually.

## 7. Tag

```bash
git tag -a v1.0.0 -m "Production go-live"
git push --tags
```

Update `docs/runbooks/cutover-history.md` with the cutover date,
operator initials, and any incidents.

## Rollback

If a critical defect is found within the first 24 h:

1. `docker compose stop backend worker frontend`.
2. `git checkout v0.16.0-tenant-portal`.
3. `docker compose up -d --build backend worker frontend`.
4. File a Sentry incident.
5. Triage, then re-cut a hotfix tag (e.g. `v1.0.1`).
