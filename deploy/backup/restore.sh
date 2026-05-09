#!/usr/bin/env bash
# Restore Landloads Postgres from a `pg_dump --format=custom` archive in MinIO.
# Usage:
#   ./restore.sh s3://landloads-backups/daily/landloads-20260509T020000Z.sql.gz
set -euo pipefail

S3_KEY="${1:-}"
[[ -z "$S3_KEY" ]] && { echo "usage: $0 s3://bucket/key"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LOCAL="$TMP/restore.dump"

echo "[$(date -u +%FT%TZ)] downloading $S3_KEY"
aws --endpoint-url "$MINIO_ENDPOINT_URL" s3 cp "$S3_KEY" "$LOCAL.gz"
gunzip "$LOCAL.gz"

echo "[$(date -u +%FT%TZ)] restoring to $POSTGRES_DB on $POSTGRES_HOST"
PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
  -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges \
  "$LOCAL"

echo "[$(date -u +%FT%TZ)] done."
