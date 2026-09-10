# DevOps Internship Project

## Overview

This project demonstrates a Flask API deployed as two application containers behind
NGINX, with PostgreSQL for records and Redis for a shared counter. Part 1 analyzes
three historical incident logs. Parts 2 and 3 provide the Docker Compose topology,
health checks, validation, failure testing, database backup/restore scripts, and CI
workflow.

The repository contains synthetic lab data only.

## Architecture

```text
Host :8080
    |
    v
NGINX :80 (container nginx)
    |
    +--> app-01 :8080
    |
    +--> app-02 :8080
             |
             +--> PostgreSQL :5432
             +--> Redis :6379
```

`nginx`, `app-01`, and `app-02` share `barq-frontend`. The two application
containers, `postgres`, and `redis` share the internal `barq-backend` network.
NGINX is deliberately not on the backend network. PostgreSQL, Redis, and Flask
have no host port mappings.

The architecture diagram is [architecture.png](architecture.png).

## Prerequisites

- Docker Desktop with Docker Compose and Linux containers
- Git
- `curl` for endpoint demonstrations
- Bash/WSL for `backup.sh` and `restore.sh`

The required container names must be available: `app-01`, `app-02`, `nginx`,
`postgres`, and `redis`. An existing unrelated container with one of these names
will prevent Compose from starting this lab.

## Configuration

Create a local environment file from the safe template:

```bash
cp .env.example .env
```

Set a local PostgreSQL password in `.env`. `.env` is ignored by Git; never commit
it. `.env.example` contains placeholders only. Compose reads the values and builds
`DATABASE_URL` with the Docker service name `postgres`.

## Setup, build and start

```bash
git clone <repository-url>
cd barq-academy
cp .env.example .env
# Edit .env and replace CHANGE_ME_LOCAL_ONLY

docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

The expected services are `postgres`, `redis`, `app-01`, `app-02`, and `nginx`,
with health checks eventually showing `healthy`.

## Stop and cleanup

Normal cleanup stops and removes containers and networks while preserving named
volumes:

```bash
docker compose down
```

Do not use `docker compose down -v` during persistence work. The `-v` form removes
named volumes and can destroy PostgreSQL and Redis data. Use it only when deliberate
data destruction is acceptable.

## Endpoints and validation

The API implements:

- `/`: application message and backend identity
- `/health`: Flask process liveness
- `/ready`: PostgreSQL and Redis readiness
- `/instance`: backend identity
- `GET /records`: PostgreSQL records
- `POST /records`: create a PostgreSQL record
- `/counter`: Redis-backed atomic counter

Once the stack is healthy, test manually:

```bash
curl -sS http://127.0.0.1:8080/
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/ready
curl -sS http://127.0.0.1:8080/instance
curl -sS http://127.0.0.1:8080/records
curl -sS -H 'Content-Type: application/json' \
  -d '{"title":"manual verification"}' \
  http://127.0.0.1:8080/records
curl -sS http://127.0.0.1:8080/counter
```

Automated validation is:

```bash
python validate.py
```

It uses bounded waits and request timeouts. Every check prints `PASS` or `FAIL`.
It verifies Compose configuration, Compose-owned healthy containers, public NGINX
access, all endpoints, both backend identities, network isolation, and host-port
exposure. It exits `0` only when all checks pass and exits non-zero on failure.

The validator was executed on this workstation and correctly returned `RESULT:
FAIL` because the required Compose stack was not running. Runtime validation could
not proceed because an old exited container named `/redis` occupied the required
name; it was not removed.

## Failure and recovery test

```bash
python failure_test.py
```

The script measures 10 baseline requests, stops only `app-01`, measures 10 requests
through the surviving backend, restores `app-01`, waits up to 60 seconds for its
health check, and measures 20 recovery requests. It reports attempted requests,
successes, server errors, and identities. It exits non-zero if baseline traffic is
unavailable, traffic fails during the outage, or the recovered `app-01` is not
observed serving requests.

No runtime failure-test result is claimed because the stack could not start on this
workstation.

## Backup and restore

Create a PostgreSQL custom-format backup using `pg_dump` inside the database
container:

```bash
bash backup.sh
```

Backups are timestamped under `backups/`, are ignored by Git, and must be non-empty.
PostgreSQL remains unpublished to the host.

Restore into the controlled test database `barq_restore_test`:

```bash
bash restore.sh backups/postgres-<timestamp>.dump
```

The script uses `pg_restore`, queries the restored `records` table, and does not
delete the primary application database or named volume. Backup/restore execution
has not been claimed as passing because the Docker stack was unavailable.

## Persistence test

After successful startup:

```bash
record_title="persistence-$(date -u +%Y%m%dT%H%M%SZ)"
curl -sS -H 'Content-Type: application/json' \
  -d "{\"title\":\"$record_title\"}" \
  http://127.0.0.1:8080/records

docker compose up -d --force-recreate postgres app-01 app-02
python validate.py
curl -sS http://127.0.0.1:8080/records
```

Search the returned records for the known title. `--force-recreate` preserves the
named volume `barq-postgres-data` mounted at `/var/lib/postgresql/data`. Do not use
`docker compose down -v`. Persistence has not been runtime-proven on this machine.

Inspect volumes without deleting them:

```bash
docker volume ls
docker volume inspect barq-postgres-data
docker volume inspect barq-redis-data
```

## Ports and networks

Only this host mapping is configured:

```text
Host 8080 -> nginx container 80
```

Internal service ports are NGINX-to-Flask `8080`, Flask-to-PostgreSQL `5432`, and
Flask-to-Redis `6379`. Service names are used for Docker DNS; container IPs are not
hard-coded. Keeping backend services unpublished prevents direct host access.

Inspect the topology:

```bash
docker network inspect barq-frontend
docker network inspect barq-backend
docker ps
```

Expected membership:

```text
barq-frontend: nginx, app-01, app-02
barq-backend:  app-01, app-02, postgres, redis
```

## Health, readiness and resources

- PostgreSQL uses `pg_isready` every 5 seconds, with 10 retries and a 10-second start period.
- Redis uses `redis-cli ping` every 5 seconds, with 5 retries and a 5-second start period.
- Flask uses Python's standard-library HTTP client against `/health` every 5 seconds, with 5 retries and a 10-second start period.
- NGINX uses its installed `wget` against `/health` every 5 seconds, with 5 retries.
- Apps wait for healthy PostgreSQL and Redis; NGINX waits for healthy apps.
- Services use `restart: unless-stopped`.
- App, PostgreSQL, Redis, and NGINX have Compose CPU/memory limits.

The Python image is `python:3.12-slim-bookworm`, pinned by digest. The application
runs as UID 10001 rather than root. Gunicorn is used because the container needs a
production-style WSGI server instead of Flask's development server.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on pushes and pull
requests:

```text
checkout -> Python syntax -> Compose config -> build -> start
-> bounded health wait -> validate.py -> docker compose down
```

Cleanup runs with `if: always()` and does not remove volumes. A green run would
prove the checked-out code builds and passes this local Compose validation in the
GitHub runner. It would not prove production-scale capacity, long-term availability,
disaster recovery, external dependencies, or real secret management. No GitHub
Actions run URL is recorded because this repository has not had a verified CI run
in this environment.

## Part 1 investigation

Run the historical log analysis with:

```bash
python scripts/analyze_logs.py
```

The report in [log_analysis.md](log_analysis.md) contains the actual counts,
timeline, correlations, hypotheses, failed attempts, and limits. The original
`logs/access.log`, `logs/error.log`, and `logs/application.log` remain unchanged.

## Required questions and remaining improvements

The historical logs show the first incident wave as NGINX connection refusals at
11:05 UTC, proven by `connect() failed` messages and matching 502 responses. Later
waves show Redis timeouts, PostgreSQL invalid-password errors, and upstream
read timeouts. Request IDs prevent double-counting.

Remaining single points of failure are NGINX, PostgreSQL, Redis, the Docker host,
and the named storage. Production improvements would include redundant NGINX,
managed/high-availability PostgreSQL and Redis, encrypted and access-controlled
backups, centralized metrics/tracing, vulnerability scanning, and a secret manager.
These are recommendations, not implemented claims.
