"""
Test all routes for caching behavior.
Usage: python scripts/test_caching.py
Requires: server running at http://localhost:8000
"""
import urllib.request
import urllib.parse
import json
import sys
import time

BASE = "http://localhost:8000"
USERNAME = "24520378"
PASSWORD = "lelelele1029"


def req(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}


def test_route(name, method, path, data=None, token=None):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    result = req(method, path, data, token)
    cached = result.get("cached", "N/A")
    success = result.get("success", False)
    timings = result.get("timings_ms", {})
    print(f"  success: {success}")
    print(f"  cached:  {cached}")
    print(f"  timings: {timings}")
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        if "detail" in result:
            print(f"  detail: {result['detail']}")
    return result


# Step 1: Login
print("="*60)
print("  STEP 1: LOGIN")
print("="*60)
login_result = test_route("POST /auth/login", "POST", "/auth/login", {
    "username": USERNAME,
    "password": PASSWORD,
})
token = login_result.get("token")
if not token:
    print("\n  ❌ LOGIN FAILED - cannot continue")
    sys.exit(1)
print(f"\n  ✅ Token: {token[:20]}...")

# Step 2: First call to /schedule/ (should be cache miss)
print("\n" + "="*60)
print("  STEP 2: /schedule/ (first call - expect cached: false)")
print("="*60)
r1 = test_route("GET /schedule/", "GET", "/schedule/", token=token)

# Step 3: Second call to /schedule/ (should be cache hit)
print("\n" + "="*60)
print("  STEP 3: /schedule/ (second call - expect cached: true)")
print("="*60)
r2 = test_route("GET /schedule/", "GET", "/schedule/", token=token)

# Step 4: /schedule/exam
print("\n" + "="*60)
print("  STEP 4: /schedule/exam (first call)")
print("="*60)
r3 = test_route("GET /schedule/exam", "GET", "/schedule/exam?lanthi=1&hocky=1&namhoc=2025", token=token)

print("\n" + "="*60)
print("  STEP 5: /schedule/exam (second call - expect cached: true)")
print("="*60)
r4 = test_route("GET /schedule/exam", "GET", "/schedule/exam?lanthi=1&hocky=1&namhoc=2025", token=token)

# Step 6: /grades/
print("\n" + "="*60)
print("  STEP 6: /grades/ (first call)")
print("="*60)
r5 = test_route("GET /grades/", "GET", "/grades/", token=token)

print("\n" + "="*60)
print("  STEP 7: /grades/ (second call - expect cached: true)")
print("="*60)
r6 = test_route("GET /grades/", "GET", "/grades/", token=token)

# Step 8: /tuition/
print("\n" + "="*60)
print("  STEP 8: /tuition/ (first call)")
print("="*60)
r7 = test_route("GET /tuition/", "GET", "/tuition/", token=token)

print("\n" + "="*60)
print("  STEP 9: /tuition/ (second call - expect cached: true)")
print("="*60)
r8 = test_route("GET /tuition/", "GET", "/tuition/", token=token)

# Step 10: /deadlines/
print("\n" + "="*60)
print("  STEP 10: /deadlines/ (first call)")
print("="*60)
r9 = test_route("GET /deadlines/", "GET", "/deadlines/", token=token)

print("\n" + "="*60)
print("  STEP 11: /deadlines/ (second call - expect cached: true)")
print("="*60)
r10 = test_route("GET /deadlines/", "GET", "/deadlines/", token=token)

# Summary
print("\n\n" + "="*60)
print("  CACHING TEST SUMMARY")
print("="*60)
results = [
    ("/schedule/ (1st)", r1.get("cached")),
    ("/schedule/ (2nd)", r2.get("cached")),
    ("/schedule/exam (1st)", r3.get("cached")),
    ("/schedule/exam (2nd)", r4.get("cached")),
    ("/grades/ (1st)", r5.get("cached")),
    ("/grades/ (2nd)", r6.get("cached")),
    ("/tuition/ (1st)", r7.get("cached")),
    ("/tuition/ (2nd)", r8.get("cached")),
    ("/deadlines/ (1st)", r9.get("cached")),
    ("/deadlines/ (2nd)", r10.get("cached")),
]
for name, cached in results:
    status = "✅" if cached is True else ("❌" if cached is False else "⚠️")
    print(f"  {status} {name}: cached={cached}")