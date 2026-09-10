#!/usr/bin/env python3
"""Bounded validation for the Compose deployment."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = os.environ.get("VALIDATION_URL", "http://127.0.0.1:8090")
COMPOSE = ["docker", "compose"]
SERVICES = ["app-01", "app-02", "nginx", "postgres", "redis"]


def run(command, check=False):
	result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
	if check and result.returncode:
		raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
	return result


def report(name, passed, detail=""):
	print(f"{'PASS' if passed else 'FAIL'}: {name}{(' - ' + detail) if detail else ''}")
	return passed


def wait_for(predicate, timeout=60, interval=2):
	deadline = time.monotonic() + timeout
	while time.monotonic() < deadline:
		if predicate():
			return True
		time.sleep(interval)
	return False


def health(name):
	result = run(["docker", "inspect", "--format", "{{.State.Status}}|{{.State.Health.Status}}|{{index .Config.Labels \"com.docker.compose.project\"}}", name])
	if result.returncode:
		return False
	state, health_status, project = result.stdout.strip().split("|", 2)
	return state == "running" and health_status == "healthy" and project == "barq-assessment"


def compose_container_exists(name):
	result = run(["docker", "inspect", "--format", "{{index .Config.Labels \"com.docker.compose.project\"}}|{{.State.Status}}", name])
	return result.returncode == 0 and result.stdout.strip() == "barq-assessment|running"


def request(path, method="GET", body=None):
	data = None if body is None else json.dumps(body).encode()
	request_obj = urllib.request.Request(BASE_URL + path, data=data, method=method)
	if data:
		request_obj.add_header("Content-Type", "application/json")
	try:
		with urllib.request.urlopen(request_obj, timeout=5) as response:
			payload = response.read().decode()
			return response.status, json.loads(payload)
	except urllib.error.HTTPError as error:
		try:
			payload = json.loads(error.read().decode())
		except (ValueError, UnicodeDecodeError):
			payload = {}
		return error.code, payload
	except (OSError, ValueError):
		return None, {}


def container_ports():
	result = run(["docker", "ps", "--format", "{{json .}}"])
	if result.returncode:
		return {}
	ports = {}
	for line in result.stdout.splitlines():
		row = json.loads(line)
		ports[row["Names"]] = row.get("Ports", "")
	return ports


def network_members(network):
	result = run(["docker", "network", "inspect", network])
	if result.returncode:
		return set()
	data = json.loads(result.stdout)[0]
	return {container["Name"].lstrip("/") for container in data.get("Containers", {}).values()}


def main():
	passed = True
	config = run(COMPOSE + ["config", "--quiet"])
	passed &= report("Docker Compose configuration", config.returncode == 0, config.stderr.strip())
	if not config.returncode:
		containers_ready = True
		for service in SERVICES:
			exists = compose_container_exists(service)
			containers_ready &= exists
			passed &= report(f"running Compose container: {service}", exists)
		if not containers_ready:
			print("RESULT: FAIL")
			return 1
		for service in SERVICES:
			ready = wait_for(lambda service=service: health(service), timeout=30)
			passed &= report(f"healthy: {service}", ready)

		status, root = request("/")
		passed &= report("NGINX public access", status == 200 and "instance_id" in root)
		for path in ["/health", "/ready", "/instance"]:
			status, payload = request(path)
			passed &= report(f"GET {path}", status == 200 and isinstance(payload, dict))
		status, payload = request("/records")
		passed &= report("GET /records", status == 200 and isinstance(payload.get("records"), list))
		title = f"validation-{uuid.uuid4().hex[:10]}"
		status, payload = request("/records", "POST", {"title": title})
		passed &= report("POST /records", status == 201 and payload.get("record", {}).get("title") == title)
		status, payload = request("/counter")
		passed &= report("GET /counter", status == 200 and isinstance(payload.get("counter"), int))

		identities = set()
		for _ in range(12):
			status, payload = request("/instance")
			if status == 200:
				identities.add(payload.get("instance_id"))
		passed &= report("both application backends observed", identities == {"app-01", "app-02"}, ", ".join(sorted(identities)))

		frontend = network_members("barq-frontend")
		backend = network_members("barq-backend")
		passed &= report("frontend network isolation", {"nginx", "app-01", "app-02"}.issubset(frontend) and not {"postgres", "redis"} & frontend)
		passed &= report("backend network isolation", {"app-01", "app-02", "postgres", "redis"}.issubset(backend) and "nginx" not in backend)

		ports = container_ports()
		passed &= report("only NGINX publishes a host port", "8080->80" in ports.get("nginx", "") and all(not ports.get(name) for name in ["app-01", "app-02", "postgres", "redis"]), str(ports))
		expected_port = urllib.parse.urlparse(BASE_URL).port or int(os.environ.get("PUBLIC_PORT", "8080"))
		nginx_port_mapped = f"{expected_port}->80" in ports.get("nginx", "")
		backends_unexposed = all("->" not in ports.get(name, "") for name in SERVICES if name != "nginx")
		passed &= report("only NGINX publishes a host port", nginx_port_mapped and backends_unexposed, str(ports))

	print(f"RESULT: {'PASS' if passed else 'FAIL'}")
	return 0 if passed else 1


if __name__ == "__main__":
	sys.exit(main())
