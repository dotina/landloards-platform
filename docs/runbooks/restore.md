# Database restore drill (must run quarterly)

This drill verifies that the daily `pg_dump` archives in MinIO can be
restored into a clean Postgres in under 30 minutes. Required by design §8
(deletion + 7-year retention) and the Phase 16 go-live gate.

## Pre-requisites

- A staging Postgres instance reachable at `STAGING_PG_HOST:5432`.
- MinIO credentials with read access to the `landloads-backups` bucket.
- `aws` CLI v2, `pg_restore` 16+, `gunzip`.

## Procedure

1. List the latest backup:
   ```bash
   aws --endpoint-url "$MINIO_ENDPOINT_URL" s3 ls s3://landloads-backups/daily/
   ```
2. Pick the most recent key, then run:
   ```bash
   POSTGRES_HOST=$STAGING_PG_HOST \
   POSTGRES_DB=landloads_restore_drill \
   POSTGRES_USER=landloads \
   POSTGRES_PASSWORD=$STAGING_PG_PASSWORD \
   POSTGRES_PORT=5432 \
   ./deploy/backup/restore.sh \
     s3://landloads-backups/daily/landloads-<latest>.sql.gz
   ```
3. Validate:
   ```sql
   SELECT count(*) FROM users;
   SELECT count(*) FROM payments WHERE status = 'success';
   SELECT max(created_at) FROM audit_event;  -- must be within 24 h of now
   ```
4. Drop the drill database:
   ```sql
   DROP DATABASE landloads_restore_drill;
   ```

## Acceptance

- Restore completes in < 30 minutes from a 14-day-old archive.
- Row counts match the production dashboard within 1%.
- The latest `audit_event.created_at` is within 24 h of the dump time.
- The drill is recorded in `docs/runbooks/restore-history.md` (date,
  archive key, duration, operator).

## Failure paths

- **Missing extension `pgcrypto`** — `CREATE EXTENSION IF NOT EXISTS
  pgcrypto;` then re-run `pg_restore`.
- **Permission denied on `audit_event`** — the migration grant is
  enforced; run as the `landloads` superuser for the drill, *not*
  the application role.
- **Out of disk** — dumps are ~10–50 MiB at MVP scale, so this should
  not occur until well past 100 active landlords. If it does, prune
  archives older than 30 d (`RETENTION_DAYS=30 ./backup.sh`).
