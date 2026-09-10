# Troubleshooting journal

## Entry 1 / 2026-09-07 / log investigation

- Symptom: `log_analysis.md` was a blank template and the three supplied logs
	needed analysis without changing their originals.
- Hypothesis: access and application logs are JSON Lines correlatable by
	`request_id`; the error log is NGINX text.
- Command or test: `python3 scripts/analyze_logs.py`.
- Actual output: access had 726 physical, 725 valid, 1 malformed and 5
	duplicate lines; application had 730 physical, 729 valid, 1 malformed and 49
	repeated IDs; there were 720 final access IDs, status counts
	`{200: 615, 404: 10, 502: 40, 503: 47, 504: 8}`, 95 server failures,
	13.1944% error rate, median 0.054 seconds and p95 2.001 seconds.
- Failed attempt and what changed my thinking: one wrapper command tried to enter
	`barq-academy` from an already nested directory and reported a path error.
	Rerunning from the repository root succeeded. An exploratory status counter
	also assumed every application record had `status`; handling dependency events
	without that field exposed the 47 application dependency errors.
- Root cause: the historical records contain malformed lines, repeated IDs,
	proxy failures, and application dependency events with different schemas.
- Fix: added read-only `scripts/analyze_logs.py` and completed `log_analysis.md`
	with commands, counts, correlations, timeline, and evidence limits.
- Retest evidence: the analyzer completed successfully from the repository root;
	it only reads the logs and does not write them.
- Related commit: the Part 1 investigation commit containing this entry.
- Remaining uncertainty: logs alone cannot identify why the backend was down, why
	dependencies timed out, or why the database password was invalid.

## Issue 2 - Part 2 deployment configuration

### Symptom

The starter deployment contained mismatched ports and topology: the apps bound to
`127.0.0.1`, `app-02` used the `app-01` identity, NGINX referenced `app-01:8081`,
backend services published host ports, PostgreSQL used tmpfs, and health checks
targeted `/healthz` instead of `/health`.

### Initial hypothesis

The Compose and NGINX configuration, rather than Flask endpoint code, controlled
these failures.

### Investigation command

```bash
Get-Content Dockerfile
Get-Content docker-compose.yml
Get-Content nginx/nginx.conf
Get-Content config/app.env
docker compose config --quiet
```

### Result

The configuration inspection confirmed each mismatch. `docker compose config --quiet`
passed after the corrected configuration was applied, and `docker compose build`
completed successfully.

### Interpretation

The application already had the required endpoint semantics and real PostgreSQL and
Redis dependency calls. The deployment layer was the controlling code path.

### Failed attempt

`docker compose up -d` could not create the required stack because an old exited
container named `/redis` already existed without Compose ownership labels:

```text
Conflict. The container name "/redis" is already in use
```

The partial PostgreSQL container and networks created by this attempt were removed
with `docker compose down`; named volumes were not removed. The unrelated `/redis`
container was deliberately left untouched.

### Revised hypothesis

The configuration is syntactically valid and the image builds, but runtime behavior
cannot be proven until the required container names are available.

### Root cause

Confirmed configuration defects were corrected. Runtime startup remains blocked by
the external container-name conflict, which is a workstation condition rather than
a repository configuration result.

### Fix

Part 2 commit `3944ad0` corrected service URLs, identities, network membership,
health checks, persistence mounts, non-root execution, and NGINX upstream ports.

### Retest

```bash
docker compose config --quiet
docker compose build
```

### Result

Both commands passed. Full runtime testing was not claimed.

## Issue 3 - Part 3 validation and evidence

### Symptom

`validate.py`, `failure_test.py`, `backup.sh`, and `restore.sh` were placeholders.

### Initial hypothesis

The missing deliverables could be implemented using Docker Compose commands, Python
standard-library HTTP requests, bounded retries, and PostgreSQL tools inside the
database container.

### Investigation command

```bash
python -m py_compile app/server.py validate.py failure_test.py scripts/analyze_logs.py
docker compose config --quiet
python validate.py
```

### Result

Python compilation and Compose configuration passed. The validator printed explicit
failures and returned exit code 1 because the five required Compose-owned containers
were not running.

### Interpretation

The validation failure was correct evidence that the environment was unavailable;
it was not converted into a false success.

### Fix

Commit `26fb406` implemented bounded validation, backend failure/recovery measurement,
and PostgreSQL backup/restore scripts. Commit `c618aab` added CI and evidence
documentation.

### Retest

```bash
python -m py_compile validate.py failure_test.py
python validate.py
```

### Result

The scripts compile. `validate.py` returns non-zero with `RESULT: FAIL` until the
container-name conflict is resolved. Failure testing, backup/restore, persistence,
and a GitHub Actions run remain unverified.
