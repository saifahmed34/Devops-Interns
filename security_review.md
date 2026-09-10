# Security Review

This review separates implemented controls from production recommendations. It does
not claim runtime verification where the Docker stack could not start.

## Risk 1 - Secrets in local configuration

### Current implementation
`.env` and `.env.*` are ignored while `.env.example` contains only a placeholder.
The previous tracked `config/app.env` was removed in Part 2.

### Risk
A real password in Git history or a copied local file could be exposed.

### Improvement
Implemented: use local `.env` and Compose interpolation. Production plan: use a
secret manager or Docker secrets and rotate credentials.

### Status
Implemented locally; production secret management remains a plan.

## Risk 2 - Backend host exposure

### Current implementation
Only `${PUBLIC_PORT:-8080}:80` is configured for NGINX. Flask, PostgreSQL, and
Redis have no `ports` mappings.

### Risk
Publishing backend ports would bypass NGINX controls and expose databases.

### Improvement
Implemented in Compose. Runtime port inspection remains unverified because the
required stack could not start.

### Status
Implemented configuration; runtime verification pending.

## Risk 3 - Container privileges

### Current implementation
The application image creates UID 10001 and runs Gunicorn as `app`. Services use
`no-new-privileges:true` and no service is privileged.

### Risk
Root or unnecessary Linux privileges increase impact after compromise.

### Improvement
Implemented for the application and Compose services. Production should also use
capability dropping and read-only filesystems where compatible.

### Status
Implemented configuration; runtime user inspection pending.

## Risk 4 - Image and dependency supply chain

### Current implementation
Python, PostgreSQL, Redis, and NGINX images are pinned by digest. Python dependencies
are declared in `requirements.txt`.

### Risk
Pinned images can still contain vulnerabilities and application dependencies can
become outdated.

### Improvement
Production plan: add Dependabot or equivalent updates, SBOM generation, and a
reliable image scanner. No scanner was added because it was not verified locally.

### Status
Digest pinning implemented; scanning is a production recommendation.

## Risk 5 - Network overreach

### Current implementation
NGINX is on `barq-frontend` only. Apps are on frontend and internal backend.
PostgreSQL and Redis are on backend only.

### Risk
A proxy attached to the backend network could directly reach databases and Redis.

### Improvement
Implemented in Compose. Runtime `docker network inspect` evidence is still pending.
Production should enforce policy at the orchestration layer too.

### Status
Implemented configuration; runtime verification pending.

## Risk 6 - Backup confidentiality and recovery

### Current implementation
`backup.sh` uses `pg_dump` inside the PostgreSQL container and writes custom-format
files under ignored `backups/`. `restore.sh` restores only a controlled
`barq_restore_test` database.

### Risk
Database dumps contain application data and could be copied or stored without
access control. An untested backup is not a recovery plan.

### Improvement
Implemented safe primary-database boundary. Production plan: encrypt dumps, restrict
permissions, store off-host, retain multiple versions, and run scheduled restore
rehearsals.

### Status
Scripts implemented; actual backup/restore execution is unverified.

## Risk 7 - Observability and sensitive logging

### Current implementation
Application and NGINX emit request IDs and structured request events. Startup no
longer logs connection URLs.

### Risk
Logs may still contain request metadata, and there is no central alerting or metric
pipeline.

### Improvement
Implemented secret-URL removal and correlation IDs. Production plan: centralize
logs, redact sensitive fields, add latency/error metrics, and alert on health failures.

### Status
Partial implementation; monitoring is a production plan.

## Risk 8 - Availability single points

### Current implementation
Two app instances sit behind NGINX, with restart policies and health-aware startup.

### Risk
NGINX, PostgreSQL, Redis, the Docker host, and named storage remain single points
of failure. Two app containers do not provide database or edge redundancy.

### Improvement
Production plan: redundant edge/load balancers, replicated PostgreSQL and Redis,
health-based scheduling, multi-host storage, and tested disaster recovery.

### Status
Application redundancy implemented in configuration; runtime failure recovery was
not verified because the stack could not start.

## Risk 9 - Resource exhaustion

### Current implementation
Compose sets CPU and memory limits for the app, PostgreSQL, Redis, and NGINX.

### Risk
Limits that are too low can cause instability; limits that are absent can let one
service starve the host.

### Improvement
Implemented initial local limits. Production plan: tune them from observed usage,
set alerts, and define service-level objectives.

### Status
Implemented configuration; runtime resource behavior not measured.

## Risk 10 - Dependency readiness and restart loops

### Current implementation
Health checks use bounded intervals/retries, app startup waits for healthy database
and Redis, and services use `unless-stopped`.

### Risk
A permanently broken dependency can cause repeated restarts and obscure the root
cause.

### Improvement
Implemented bounded checks. Production plan: add exponential backoff, restart-loop
alerts, and dependency circuit-breaking where appropriate.

### Status
Implemented configuration; runtime transitions pending.
