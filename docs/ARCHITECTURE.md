# Architecture

The rendered diagram is [architecture.png](../architecture.png).

## Request flow

The only configured host mapping is `8080:80` for NGINX. NGINX listens on
container port 80 and load-balances to `app-01:8080` and `app-02:8080` using Docker
service discovery. The Flask containers use internal port 8080.

## Networks

- `barq-frontend`: `nginx`, `app-01`, `app-02`
- `barq-backend`: `app-01`, `app-02`, `postgres`, `redis`

`barq-backend` is internal and NGINX is not attached to it. This allows apps to
reach dependencies without giving the edge proxy direct database/cache network
access.

## Dependencies and storage

Both app containers use `postgres:5432` for PostgreSQL and `redis:6379` for Redis.
PostgreSQL uses named volume `barq-postgres-data` mounted at
`/var/lib/postgresql/data`. Redis uses named volume `barq-redis-data` mounted at
`/data` and runs append-only persistence with `everysec` fsync.

## Health relationships

PostgreSQL uses `pg_isready`; Redis uses `redis-cli ping`; apps use Python's standard
library against `/health`; NGINX uses its installed `wget` against `/health`.
Compose starts apps only after PostgreSQL and Redis are healthy, and starts NGINX
only after both apps are healthy. The repository configuration expresses these
relationships; runtime transitions were not verified on the workstation because an
unrelated exited `/redis` container occupied the required name.

## Availability limits

Two app containers provide application-level redundancy. NGINX, PostgreSQL, Redis,
the Docker host, and the named storage remain single points of failure in this
local architecture. Production would require redundant edge capacity, replicated
databases/caches, multi-host scheduling, and tested disaster recovery.
