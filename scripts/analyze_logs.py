#!/usr/bin/env python3
"""Analyze the supplied incident logs without changing them."""
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"


def parse_json_log(name):
    records = []
    malformed = []
    for line_number, line in enumerate((LOGS / name).read_text().splitlines(), 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            malformed.append((line_number, line, str(error)))
    return records, malformed


def percentile(values, rank):
    ordered = sorted(values)
    position = (len(ordered) - 1) * rank
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def main():
    access, access_bad = parse_json_log("access.log")
    application, application_bad = parse_json_log("application.log")
    errors = (LOGS / "error.log").read_text().splitlines()

    print("FILE QUALITY")
    for name, records, malformed in (("access.log", access, access_bad), ("application.log", application, application_bad)):
        ids = [record.get("request_id") for record in records]
        counts = Counter(ids)
        duplicates = sum(count - 1 for count in counts.values() if count > 1)
        print(f"{name}: physical={len(records) + len(malformed)} valid={len(records)} malformed={len(malformed)} unique_request_ids={len(counts)} duplicate_lines={duplicates}")
        for line_number, line, reason in malformed:
            print(f"  malformed line {line_number}: {line!r} ({reason})")
    print(f"error.log: physical={len(errors)} valid_text={len(errors)}")

    by_id = defaultdict(list)
    for record in access:
        by_id[record["request_id"]].append(record)
    final = [records[-1] for records in by_id.values()]
    status_counts = Counter(record["status"] for record in final)
    failures = [record for record in final if record["status"] >= 500]
    print("FINAL ACCESS REQUESTS")
    print(f"distinct_requests={len(final)} status_counts={dict(sorted(status_counts.items()))}")
    print(f"methods={dict(Counter(record['method'] for record in final))}")
    print(f"paths={dict(Counter(record['path'] for record in final))}")
    print(f"clients={dict(Counter(record['client'] for record in final))}")
    print(f"server_failures={len(failures)} error_rate={len(failures) / len(final):.4%} denominator={len(final)}")
    print(f"failure_paths={dict(Counter(record['path'] for record in failures))}")
    print(f"failure_backends={dict(Counter(record['upstream'] for record in failures))}")
    print(f"failure_windows={dict(Counter(record['timestamp'][:16] for record in failures))}")

    latencies = [record["request_time"] for record in final]
    print(f"latency_seconds median={statistics.median(latencies):.6f} p95={percentile(latencies, 0.95):.6f} method=linear_interpolation_position_(n-1)*p units=seconds")

    app_by_id = defaultdict(list)
    for record in application:
        app_by_id[record["request_id"]].append(record)
    retried = {request_id: records for request_id, records in app_by_id.items() if len(records) > 1}
    succeeded = sum(records[-1].get("status", 599) < 500 for records in retried.values())
    print(f"retried_request_ids={len(retried)} retried_succeeded={succeeded}")
    print("retry_examples=" + ",".join(sorted(retried)[:10]))

    error_ids = [match.group(1) for line in errors if (match := re.search(r"request_id=(lab-\d+)", line))]
    error_types = Counter("connect_refused" if "connect() failed" in line else "upstream_timeout" if "upstream timed out" in line else "notice" if "[notice]" in line else "other" for line in errors)
    app_events = Counter(record.get("event") for record in application)
    dependency_errors = Counter((record.get("dependency"), record.get("error_type")) for record in application if record.get("event") == "dependency_error")
    print(f"error_types={dict(error_types)}")
    print(f"application_events={dict(app_events)} dependency_errors={dict(dependency_errors)}")
    print(f"error_request_ids={len(error_ids)} unique={len(set(error_ids))}")
    timestamps = [datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")) for record in final]
    print(f"utc_start={min(timestamps).isoformat()} utc_end={max(timestamps).isoformat()}")


if __name__ == "__main__":
    main()
