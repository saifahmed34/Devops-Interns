# Part 3: Validation, Persistence and CI

## Validation

Run from the repository root after creating a local `.env` from `.env.example`:

```bash
cp .env.example .env
python validate.py
```

`validate.py` first runs `docker compose config --quiet`. It then checks the five
expected Compose-owned containers, waits up to 30 seconds for each health check,
checks public NGINX access and every application endpoint, observes both backend
identities, inspects the `barq-frontend` and `barq-backend` memberships, and
checks that only NGINX publishes a host port. Each check prints `PASS` or `FAIL`.
It prints `RESULT: PASS` and exits 0 only when all checks pass; any failure exits
non-zero. Endpoint requests have a five-second timeout and backend observation is
bounded to 12 requests.

The current workstation cannot complete runtime validation because an old,
externally created exited container named `redis` occupies the required container
name. The validator correctly reports a failure until that conflict is resolved.
No container or volume was removed by the investigation.

## Failure and recovery test

```bash
python failure_test.py
```

The test measures 10 baseline requests, stops only `app-01`, measures 10 requests
through the surviving backend, restores `app-01` with `docker compose up -d`, waits
up to 60 seconds for its health check, and measures 20 recovery requests. It prints
attempted requests, successes, server errors, and observed identities. A recovery
is only accepted when `app-01` is observed serving traffic again. A `finally` block
attempts to restore `app-01` even when an intermediate assertion fails.

## PostgreSQL backup and restore

The backup uses `pg_dump` inside the PostgreSQL container, so PostgreSQL is never
published to the host:

```bash
bash backup.sh
```

The default output is a timestamped custom-format dump under `backups/`, which is
ignored by Git. The script fails if the dump is empty.

Restore is deliberately isolated to a controlled test database, not the primary
application database:

```bash
bash restore.sh backups/postgres-<timestamp>.dump
```

The script recreates only `barq_restore_test`, restores the dump with `pg_restore`,
and queries the restored `records` table. It does not delete the primary database
or PostgreSQL volume.

## Persistence test

After the stack is healthy:

```bash
record_title="persistence-$(date -u +%Y%m%dT%H%M%SZ)"
curl -sS -H 'Content-Type: application/json' \
  -d "{\"title\":\"$record_title\"}" \
  http://127.0.0.1:8080/records

docker compose up -d --force-recreate postgres app-01 app-02
python validate.py
curl -sS http://127.0.0.1:8080/records
```

The PostgreSQL named volume is `barq-postgres-data`, mounted at
`/var/lib/postgresql/data`. `--force-recreate` preserves that volume; do not use
`docker compose down -v`. The returned records list must contain the known title.

Inspect the volume without deleting it:

```bash
docker volume inspect barq-postgres-data
docker volume inspect barq-redis-data
```

## Network and port evidence

```bash
docker network inspect barq-frontend
docker network inspect barq-backend
docker ps
```

Expected topology:

- `barq-frontend`: `nginx`, `app-01`, `app-02`
- `barq-backend`: `app-01`, `app-02`, `postgres`, `redis`
- host port `8080` maps only to NGINX port `80`
- no host mappings for app, PostgreSQL, or Redis

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pushes and pull
requests. It performs Python syntax checks, Compose validation, image build, stack
startup, a bounded health wait, `python validate.py`, and unconditional
`docker compose down` cleanup. The workflow does not remove named volumes.

The workflow has not been claimed as passing until a real GitHub Actions run is
available. No run URL is recorded here without an actual run.
