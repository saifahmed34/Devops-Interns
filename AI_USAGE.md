# AI Usage

## Tools used

GitHub Copilot was used as an engineering assistant in VS Code. Shell commands,
repository tools, file reads, patches, and validation commands were executed in the
shared workspace.

## Purpose

AI assistance was used for:

- inspecting the existing repository and identifying Part 1, 2, and 3 gaps
- structuring the read-only historical-log analyzer
- reviewing Docker Compose networks, health checks, ports, volumes, and restart settings
- drafting bounded validation, failure-recovery, backup, restore, and CI structures
- drafting this documentation from repository evidence
- identifying stale counts and correcting documentation to match executable output

## Affected files

The assistance influenced these files across the completed work:

```text
scripts/analyze_logs.py
log_analysis.md
troubleshooting.md
Dockerfile
docker-compose.yml
app/server.py
nginx/nginx.conf
.env.example
config/app.env
validate.py
failure_test.py
backup.sh
restore.sh
.github/workflows/ci.yml
docs/PART3.md
README.md
decisions.md
security_review.md
AI_USAGE.md
```

Original logs under `logs/` were inspected but not modified.

## Verification

The work was independently checked with:

- repository inspection and Git history review
- `docker compose config --quiet`
- `docker compose build` for the Part 2 image
- Python compilation for application, analyzer, validation, and failure scripts
- `git diff --check`
- SHA-256 comparison proving the three original logs remained unchanged
- successful execution of `scripts/analyze_logs.py`
- deliberate execution of `validate.py`, which returned non-zero and reported the
  unavailable Docker runtime instead of being treated as a pass

Runtime endpoint, failure-recovery, backup/restore, persistence, and CI-run results
were not fabricated. They remain unverified because an old exited container named
`redis` occupied the required Compose container name and was intentionally not
removed.

## Related commits

- `9808f07 investigate: analyze historical incident logs`
- `3944ad0 refactor: update environment configuration and improve Docker setup`
- `26fb406 feat: add validation failure and database scripts`
- `c618aab ci: add compose validation workflow and evidence`
