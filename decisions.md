# Technical Decisions

These decisions describe the implementation in commits `3944ad0`, `26fb406`, and
`c618aab`. Runtime claims are limited to the checks actually executed.

## Decision 1 - NGINX is the only published service

### Decision
Publish host port `8080` only for `nginx:80`. Flask, PostgreSQL, and Redis use
internal Docker ports only.

### Reason
A single edge entry point makes routing explicit and prevents direct host access to
backend services.

### Alternatives
Publish Flask directly, or publish PostgreSQL/Redis for convenience.

### Trade-offs
NGINX becomes a single edge point, but the attack surface is smaller and the
architecture matches the assignment.

### Assumptions and limitations
The Compose file expresses the mapping, but runtime port verification is blocked
on this workstation by the stale `redis` container name conflict.

### Production improvement
Use redundant edge instances or a managed load balancer.

## Decision 2 - Separate frontend and backend networks

### Decision
`barq-frontend` contains NGINX and both apps. `barq-backend` contains both apps,
PostgreSQL, and Redis; it is marked internal. NGINX is not on the backend network.

### Reason
Applications need both edge and dependency access, while NGINX only needs the apps.

### Alternatives
Use one shared network.

### Trade-offs
The topology is slightly more configuration, but limits unnecessary connectivity.

### Assumptions and limitations
The intended memberships are statically defined; `docker network inspect` was not
completed because the stack could not start.

### Production improvement
Add network policy enforcement and separate administrative networks.

## Decision 3 - Docker service names for discovery

### Decision
Use `app-01`, `app-02`, `postgres`, and `redis` as Docker DNS names. No container
IP addresses are hard-coded.

### Reason
Container IP addresses can change when containers are recreated; service names are
stable Compose discovery names.

### Alternatives
Static IP addresses or host networking.

### Trade-offs
The services depend on Docker DNS, but this is the normal Compose model.

### Assumptions and limitations
DNS resolution is configured but not runtime-proven on this workstation.

### Production improvement
Use platform-native service discovery and authenticated transport where required.

## Decision 4 - Named volumes for PostgreSQL and Redis

### Decision
Use `barq-postgres-data` at PostgreSQL's data directory and `barq-redis-data` at
Redis `/data`. Redis uses append-only persistence with `everysec` fsync.

### Reason
PostgreSQL records must survive container recreation. Redis persistence is useful
for the shared counter and makes the choice explicit.

### Alternatives
Temporary storage or a host bind mount.

### Trade-offs
Volumes require intentional cleanup and backup management; Redis AOF adds disk I/O.

### Assumptions and limitations
Volume creation was observed, but persistence was not runtime-tested because the
stack could not start.

### Production improvement
Use encrypted, replicated storage and tested off-host backups.

## Decision 5 - Health checks and dependency-aware startup

### Decision
Use `pg_isready`, `redis-cli ping`, Python HTTP checks for Flask `/health`, and
NGINX `wget` checks. Apps wait for healthy PostgreSQL/Redis; NGINX waits for healthy
apps.

### Reason
Container creation order is not the same as service readiness. These checks test
the actual dependency boundaries.

### Alternatives
Use only `depends_on` short syntax or fixed sleeps.

### Trade-offs
Startup is slower and health checks consume small amounts of resources, but failure
is visible and bounded.

### Assumptions and limitations
The Compose syntax passed validation; health transitions were not observed due to
the runtime name conflict.

### Production improvement
Add readiness metrics and alerting on prolonged unhealthy states.

## Decision 6 - Non-root Gunicorn application

### Decision
Use Python 3.12 slim, install the declared dependencies, run Gunicorn as UID
10001, and expose only internal port 8080.

### Reason
Gunicorn is appropriate for a WSGI container and a non-root process reduces the
impact of application compromise.

### Alternatives
Flask's development server or root execution.

### Trade-offs
Gunicorn adds worker configuration and the slim image may require explicit package
choices, but the image build passed.

### Production improvement
Use a build stage, dependency lock review, and automated image scanning.

## Decision 7 - Bounded validation and CI cleanup

### Decision
`validate.py` uses finite health waits and request timeouts. CI runs config,
syntax, build, startup, bounded health checks, validation, and unconditional
`docker compose down`.

### Reason
A broken dependency must fail instead of hanging indefinitely, and CI must clean
up even after a failure.

### Alternatives
Infinite retry loops or ignoring validation failures.

### Trade-offs
Transient slow starts can fail after the defined window; the limits are explicit.

### Production improvement
Tune timeouts from measured service-level objectives and preserve diagnostic logs
as CI artifacts.
