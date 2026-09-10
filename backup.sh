#!/usr/bin/env bash
set -euo pipefail

backup_dir="${BACKUP_DIR:-backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="${backup_dir}/postgres-${timestamp}.dump"
mkdir -p "$backup_dir"

docker compose exec -T postgres pg_dump \
	--format=custom \
	--file=- \
	--username="${POSTGRES_USER:-barq_app}" \
	"${POSTGRES_DB:-barq_tasks}" > "$backup_file"

test -s "$backup_file"
printf 'PASS: PostgreSQL backup created at %s\n' "$backup_file"
