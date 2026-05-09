#!/usr/bin/env bash
# Daily Postgres backup shipped to MinIO.
#
# Schedule via cron on the host (or as a sidecar arq job):
#   0 2 * * * /root/landloads/deploy/backup/backup.sh >> /var/log/landloads-backup.log 2>&1
#
# Required env vars:
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
#   MINIO_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#   BACKUP_BUCKET (defaults to "landloads-backups")
set -euo pipefail

BUCKET="${BACKUP_BUCKET:-landloads-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

DUMP="$TMP/landloads-$STAMP.sql.gz"
echo "[$(date -u +%FT%TZ)] dumping $POSTGRES_DB to $DUMP"
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom --compress=9 \
  | gzip --no-name > "$DUMP"

SIZE_KB=$(stat -c%s "$DUMP" 2>/dev/null || stat -f%z "$DUMP")
SIZE_KB=$((SIZE_KB / 1024))
echo "[$(date -u +%FT%TZ)] dump size ${SIZE_KB} KiB"

aws --endpoint-url "$MINIO_ENDPOINT_URL" \
    s3 cp "$DUMP" "s3://$BUCKET/daily/$(basename "$DUMP")" \
    --no-progress

echo "[$(date -u +%FT%TZ)] uploaded; pruning older than $RETENTION_DAYS days"
CUTOFF=$(date -u -d "$RETENTION_DAYS days ago" +%Y%m%d 2>/dev/null \
       || date -u -v-"${RETENTION_DAYS}"d +%Y%m%d)
aws --endpoint-url "$MINIO_ENDPOINT_URL" \
    s3 ls "s3://$BUCKET/daily/" \
  | awk '{print $4}' \
  | while read -r KEY; do
      [[ -z "$KEY" ]] && continue
      KEY_DATE=$(echo "$KEY" | grep -oE '[0-9]{8}' | head -n1 || true)
      if [[ -n "$KEY_DATE" && "$KEY_DATE" < "$CUTOFF" ]]; then
        echo "[$(date -u +%FT%TZ)] pruning $KEY"
        aws --endpoint-url "$MINIO_ENDPOINT_URL" \
            s3 rm "s3://$BUCKET/daily/$KEY" >/dev/null
      fi
    done

echo "[$(date -u +%FT%TZ)] done."
