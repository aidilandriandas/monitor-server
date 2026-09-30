import urllib.request
import urllib.error
import json

API_BASE = "http://127.0.0.1:8080/api/v1"

endpoints = [
    ("GET", "/dashboard", None),
    ("GET", "/cluster/overview", None),
    ("GET", "/logs", None),
    ("GET", "/settings", None),
    ("GET", "/ai/audit", None),
    ("GET", "/ai/settings", None),
    ("GET", "/security/traffic/live", None),
    ("GET", "/security/events", None),
    ("GET", "/security/jail", None),
    ("GET", "/security/hardening", None),
    ("GET", "/security/fim", None),
    ("GET", "/security/docker-audit", None),
    ("GET", "/security/c2-miner", None),
    ("GET", "/security/perimeter", None),
    ("GET", "/process/hunter", None),
    ("GET", "/action/status?action_id=test", None),
    ("GET", "/probes", None),
    ("GET", "/network/quality", None),
    ("GET", "/runbooks", None),
    ("GET", "/ssl/certificates", None),
    ("GET", "/logs/query?limit=10", None),
    ("GET", "/network/lan-devices", None),
    ("GET", "/power/estimate", None),
    ("GET", "/proxmox/backups", None),
    ("GET", "/power/wol/devices", None),
    ("GET", "/power/vms", None),
]

print("Running Backend Endpoint Audit...")
failed = []
for method, path, data in endpoints:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            status = response.status
            print(f"[OK] {method} {path} - {status}")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] {method} {path} - HTTP {e.code}")
        failed.append(path)
    except Exception as e:
        print(f"[ERROR] {method} {path} - {e}")
        failed.append(path)

if not failed:
    print("\nAll tested GET endpoints passed!")
else:
    print(f"\nFailed endpoints: {len(failed)}")
