# Evidence Index

## Repository state

- Baseline: `8442da3`
- Part 1 investigation: `9808f07`
- Part 2 deployment configuration: `3944ad0`
- Part 3 automation: `26fb406`
- Part 3 CI/documentation: `c618aab`
- Current documentation commit: pending
- Remote currently configured as GitLab; no GitHub Actions run URL has been verified.

## Requirement map

| Requirement | Evidence | Verification status |
|---|---|---|
| Historical logs analyzed | `scripts/analyze_logs.py`, `log_analysis.md`, immutable `logs/` | Analyzer executed successfully; log hashes unchanged. |
| Investigation journal | `troubleshooting.md` | Actual commands, failed attempts, evidence, and limitations recorded. |
| Flask application endpoints | `app/server.py`, `tests/test_app.py` | App-only tests were previously blocked on host by missing `psycopg`; Docker image build passed. |
| Two app containers | `docker-compose.yml`, `Dockerfile` | Configuration implemented; runtime not verified because `/redis` name conflict blocked startup. |
| NGINX routing | `nginx/nginx.conf` | Configuration reviewed; runtime load balancing not verified. |
| Network isolation | `docker-compose.yml`, `docs/ARCHITECTURE.md`, `architecture.png` | Configuration documented; `docker network inspect` not completed. |
| Health/readiness | `docker-compose.yml`, `app/server.py`, `validate.py` | Syntax/config checks passed; health transitions not runtime-verified. |
| Validation | `validate.py` | Executed and correctly returned `RESULT: FAIL`, exit 1, when services were unavailable. |
| Failure recovery | `failure_test.py` | Implemented; not executed successfully because runtime was unavailable. |
| PostgreSQL backup/restore | `backup.sh`, `restore.sh` | Implemented; not executed successfully because runtime was unavailable. |
| Persistence | `docs/PART3.md`, named volume in `docker-compose.yml` | Procedure documented; not runtime-proven. |
| CI workflow | `.github/workflows/ci.yml` | Workflow committed; no hosted run URL verified. |
| Architecture diagram | `architecture.png`, `docs/ARCHITECTURE.md` | Generated and reviewed against Compose configuration. |
| Security review | `security_review.md` | Ten concrete findings, implemented controls, and production plans recorded. |
| AI disclosure | `AI_USAGE.md` | Tools, affected files, verification, and limitations recorded. |

## Important limitation

No document claims full runtime success. An old exited container named `/redis`, with
no Compose ownership labels, occupied the required container name. It was deliberately
not removed. This prevented startup and therefore prevented honest claims about endpoint
traffic, load balancing, network membership, failure recovery, persistence, backup/
restore execution, or a GitHub Actions run.
