#!/usr/bin/env bash
# ============================================================
# TAREA 7: Script de backup — configúralo con cron
# ============================================================
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/backups"
BACKUP_FILE="bookvault_${TIMESTAMP}.sql.gz"
S3_BUCKET="bookvault-backups"
AWS_ENDPOINT="http://localhost:4566"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup..."

# Dump de la base de datos
docker exec bookvault-db pg_dump \
    -U bookvault \
    -d bookvault \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

echo "[$(date)] Dump completed: ${BACKUP_FILE}"

# Subir a S3 (LocalStack)
aws --endpoint-url="${AWS_ENDPOINT}" \
    s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" \
    "s3://${S3_BUCKET}/db-backups/${BACKUP_FILE}"

echo "[$(date)] Uploaded to S3: s3://${S3_BUCKET}/db-backups/${BACKUP_FILE}"

# Limpiar backups locales mayores a 7 días
find "${BACKUP_DIR}" -name "bookvault_*.sql.gz" -mtime +7 -delete

echo "[$(date)] Backup completed successfully"
