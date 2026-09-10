# Log analysis

Use all three supplied logs. Answer every question with commands/scripts and actual output.

1. What UTC interval is covered? How many valid, malformed and duplicate lines are in each file?
2. How many distinct client requests occurred? How did you deduplicate and avoid counting retries twice?
3. What are the final client status counts and error rate? State your denominator.
4. Which paths, time windows and backends account for the failures?
5. What are the median and p95 client latencies? State the percentile method and units.
6. Which requests retried upstream? How many succeeded after retrying?
7. Build an incident timeline using evidence from access, error AND application logs.
8. Show one correlated failed request and one successful request. Include IDs and timestamps.
9. Which errors appear to be proxy/connectivity issues versus dependency/application issues? What proves it?
10. What do the logs not prove? What would you check next in a running environment?

## Scope and method

The originals in `logs/` were read only. Reproduce this analysis with:

```bash
python3 scripts/analyze_logs.py
```

The script parses JSON Lines, reports malformed lines, and groups valid access
records by `request_id`. One final access outcome is counted per ID. The five
duplicate access pairs have the same 200 outcome, so duplicate lines are not
counted twice. Application records are retained separately for retry and
dependency-event correlation.

The access log is JSON Lines with UTC timestamp, request ID, method, path, client,
upstream, upstream status, status, and request time. The application log is JSON
Lines with timestamp, level, event, request ID, instance, and either HTTP
status/duration or dependency/error fields. The error log is NGINX text with
timestamps, severity, request ID, request, and upstream details.

Actual analyzer output:

```text
access.log: physical=726 valid=725 malformed=1 unique_request_ids=720 duplicate_lines=5
application.log: physical=730 valid=729 malformed=1 unique_request_ids=680 duplicate_lines=49
error.log: physical=68 valid_text=68
distinct_requests=720 status_counts={200: 615, 404: 10, 502: 40, 503: 47, 504: 8}
server_failures=95 error_rate=13.1944% denominator=720
latency_seconds median=0.054000 p95=2.001000 method=linear_interpolation_position_(n-1)*p units=seconds
retried_request_ids=49 retried_succeeded=2
utc_start=2026-08-20T11:00:00.015000+00:00 utc_end=2026-08-20T11:29:57.578000+00:00
```

## Results

### 1. UTC interval and file quality

The valid access interval is `2026-08-20T11:00:00.015Z` through
`2026-08-20T11:29:57.578Z` (29:57.563).

| File | Physical | Valid | Malformed | Duplicate lines/IDs |
|---|---:|---:|---:|---:|
| `access.log` | 726 | 725 | 1, line 311 | 5 |
| `application.log` | 730 | 729 | 1, line 401 | 49 repeated IDs |
| `error.log` | 68 | 68 text records | 0 detected | not applicable |

The malformed access line starts `{"timestamp":"2026-08-20T11:12:48Z","request_id":`.
The malformed application line starts `{"timestamp":"2026-08-20T11:17:00Z","event":`.

### 2. Distinct client requests and deduplication

There were **720 distinct client request IDs**. The denominator excludes the one
malformed access line and counts one final access record per ID. The five repeated
access IDs are `lab-000121`, `lab-000241`, `lab-000361`, `lab-000481`, and
`lab-000601`; each duplicate pair is 200. Application duplicates were retained
for retry/event correlation, not added to the client denominator.

### 3. Final status counts and error rate

Final access counts are: 200 = 615, 404 = 10, 502 = 40, 503 = 47, and 504 = 8.
The server-failure count is `40 + 47 + 8 = 95`, so the server error rate is
`95 / 720 = 13.1944%`. The denominator is the 720 distinct valid access IDs;
404s are excluded from this server-failure rate.

### 4. Paths, windows and backends

Failures by path: `/records` 26, `/counter` 26, `/ready` 23, `/health` 10,
and `/` 10. Failures by backend: `172.23.0.12:8080` 68 and
`172.23.0.11:8080` 27. They cluster at 11:05-11:09, 11:12-11:15,
11:20-11:21, and 11:25-11:26 UTC; the analyzer prints exact per-minute counts.

### 5. Client latency

The median is **0.054 seconds (54 ms)** and p95 is **2.001 seconds (2001 ms)**,
using final outcomes for the 720 IDs. Units are access-log `request_time`
seconds. P95 uses linear interpolation at sorted position `(n - 1) * 0.95`;
the median uses the standard middle-value method.

### 6. Upstream retries

There are **49 request IDs with multiple application events**. Two ended with a
successful 200 after an earlier event: `lab-000181` and `lab-000421`, each logged
twice by `app-01`. The logs do not expose a formal retry-attempt field, so these
are reported as retry/event evidence rather than claiming more than proven.

## Timeline and correlated examples

| UTC period | Evidence and interpretation |
|---|---|
| 11:00-11:04 | Normal 200s plus 404s establish the baseline. |
| 11:05-11:09 | `error.log` has 59 `connect() failed (111: Connection refused)` records and access has 502s, primarily against `172.23.0.12:8080`. |
| 11:12:09-11:15:52 | Application log has 31 Redis `dependency_error` events with `TimeoutError`; matching client outcomes are 503. |
| 11:17:30 | `lab-000421` is repeated and successful on `app-01`. |
| 11:20:07-11:21:45 | Application log has 16 PostgreSQL `InvalidPassword` dependency errors and matching 503 readiness outcomes. |
| 11:25:14-11:26:47 | `error.log` has 8 `upstream timed out` records and access has 8 status 504s. |

The error log contains 59 connection-refused records, 8 upstream-timeout records,
and one collector-rotation notice. The application log contains 729 valid
records: 682 HTTP events, 31 Redis timeout dependency errors, and 16 PostgreSQL
invalid-password dependency errors. No application startup or shutdown event is
present in the supplied application log.

Failed request correlation:

```text
lab-000484
access  2026-08-20T11:20:07.541Z GET /ready -> 503 via 172.23.0.12:8080, 0.041 s
app     2026-08-20T11:20:07.540Z app-02 dependency_error: postgres InvalidPassword
app     2026-08-20T11:20:07.541Z app-02 GET /ready -> 503, 41.0 ms
```

Successful request correlation:

```text
lab-000002
access  2026-08-20T11:00:02.532Z GET /health -> 200 via 172.23.0.12:8080, 0.032 s
app     2026-08-20T11:00:02.532Z app-02 GET /health -> 200, 32.0 ms
```

## Conclusions and limits

Proxy/connectivity failures are proven by NGINX's explicit `connect() failed`
messages with matching 502s. Upstream timeout failures are proven by
`upstream timed out` with matching 504s. Dependency/application failures are
proven by application `dependency_error` records naming Redis or Postgres,
specific error types, and matching 503 responses.

The logs do not prove why a backend was down, the underlying Redis condition,
the source of the wrong PostgreSQL password, or whether a timeout came from
database load, application code, or both. They do not prove data loss, payloads,
host resource pressure, or the complete retry policy. Next checks in a running
environment: container health/restart history, NGINX and app configuration,
Docker network connectivity, Redis/PostgreSQL logs and credentials, dependency
latency, host CPU/memory, and distributed tracing retry spans.

## Hypotheses tested

| Hypothesis | Test/evidence | Conclusion |
|---|---|---|
| Backend connectivity failure | Match NGINX `connect() failed (111)` lines by request ID to access 502s. | Supported for the 59 refusal records. |
| Redis outage or latency | Count application `dependency_error` events where dependency is Redis and error is `TimeoutError`; match access 503s. | Strongly supported for 31 events; the logs do not identify the infrastructure cause. |
| PostgreSQL authentication/configuration failure | Match `postgres`/`InvalidPassword` application events to access 503 readiness responses. | Supported for 16 events. |
| Slow upstream response | Match NGINX `upstream timed out` to access 504s and application durations. | Supported for 8 requests; cause of the slow response remains unresolved. |
| Client-side 404s caused the incident | Count status 404s and compare with 5xx timeline. | Rejected as the incident cause: 404s are 10 baseline unknown-route responses and do not explain the later 5xx clusters. |
