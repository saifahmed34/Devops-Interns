#!/usr/bin/env bash
set -euo pipefail

backup_file="${1:?usage: ./restore.sh backups/postgres-<timestamp>.dump}"
test -s "$backup_file"
restore_db="${RESTORE_DB:-barq_restore_test}"

docker compose exec -T postgres psql \
	--username="${POSTGRES_USER:-barq_app}" \
	--dbname=postgres \
	--command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${restore_db}' AND pid <> pg_backend_pid();" >/dev/null
docker compose exec -T postgres psql \
	--username="${POSTGRES_USER:-barq_app}" \
	--dbname=postgres \
	--command="DROP DATABASE IF EXISTS ${restore_db};"
docker compose exec -T postgres createdb \
	--username="${POSTGRES_USER:-barq_app}" \
	"$restore_db"
docker compose exec -T postgres pg_restore \
	--exit-on-error \
	--no-owner \
	--username="${POSTGRES_USER:-barq_app}" \
	--dbname="$restore_db" < "$backup_file"

count="$(docker compose exec -T postgres psql --tuples-only --no-align \
	--username="${POSTGRES_USER:-barq_app}" --dbname="$restore_db" \
	--command='SELECT count(*) FROM records;')"
printf 'PASS: restored %s; records=%s\n' "$restore_db" "$(echo "$count" | tr -d '[:space:]')"
