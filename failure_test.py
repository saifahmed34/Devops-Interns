#!/usr/bin/env python3
"""Bounded backend failure and recovery test."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = os.environ.get("VALIDATION_URL", "http://127.0.0.1:8080")


def run(command):
	return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def request():
	try:
		with urllib.request.urlopen(BASE_URL + "/instance", timeout=3) as response:
			payload = json.loads(response.read().decode())
			return response.status, payload.get("instance_id")
	except urllib.error.HTTPError as error:
		return error.code, None
	except (OSError, ValueError):
		return None, None


def measure(count):
	results = []
	for _ in range(count):
		results.append(request())
	return results


def healthy(name, timeout=60):
	deadline = time.monotonic() + timeout
	while time.monotonic() < deadline:
		result = run(["docker", "inspect", "--format", "{{.State.Status}}|{{.State.Health.Status}}", name])
		if result.returncode == 0 and result.stdout.strip() == "running|healthy":
			return True
		time.sleep(2)
	return False


def summarize(label, results):
	successful = sum(200 <= status < 400 for status, _ in results if status is not None)
	errors = sum(status is None or status >= 500 for status, _ in results)
	print(f"{label}: attempted={len(results)} successful={successful} server_errors={errors} identities={sorted({identity for _, identity in results if identity})}")
	return successful, errors


def main():
	passed = True
	baseline = measure(10)
	baseline_success, _ = summarize("Before failure", baseline)
	if baseline_success == 0:
		print("FAIL: baseline traffic is unavailable; app-01 was not stopped")
		return 1
	stopped = False
	try:
		stop = run(["docker", "compose", "stop", "app-01"])
		stopped = stop.returncode == 0
		passed &= stopped
		during = measure(10)
		during_success, during_errors = summarize("During app-01 failure", during)
		passed &= stopped and during_success > 0 and during_errors == 0
	finally:
		restore = run(["docker", "compose", "up", "-d", "app-01"])
		passed &= restore.returncode == 0 and healthy("app-01")

	recovered = measure(20)
	recovered_success, _ = summarize("After recovery", recovered)
	passed &= recovered_success > 0 and "app-01" in {identity for _, identity in recovered}
	print(f"{'PASS' if passed else 'FAIL'}: backend failure and recovery")
	return 0 if passed else 1


if __name__ == "__main__":
	sys.exit(main())
