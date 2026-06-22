"""
Quick caching test with 60s timeout per request.
"""
import urllib.request
import json
import sys

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
        resp = urllib.request.urlopen(r, timeout=60)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": e.code, "detail": body[:200]}
    except Exception as e:
        return {"error": str(e)}


# 1. Login
print("1️⃣  Logging in...")
login = req("POST", "/auth/login", {"username": USERNAME, "password": PASSWORD})
token = login.get("token")
if not token:
    print(f"   Login failed: {login.get('detail', login.get('error'))}")
    sys.exit(1)
print(f"   ✅ Token: {token[:20]}...")

# 2. Schedule - first call (should be cache miss, may take long)
print("\n2️⃣  /schedule/ (1st) — scraping...")
r = req("GET", "/schedule/", token=token)
print(f"   success={r.get('success')}, cached={r.get('cached')}, count={r.get('count')}")
print(f"   timings={r.get('timings_ms')}")
if r.get("cached") is False:
    print("   ✅ Cache miss (expected)")
else:
    print(f"   ⚠️  Unexpected cached={r.get('cached')}")

# 3. Schedule - second call (should be cache hit)
print("\n3️⃣  /schedule/ (2nd) — should be cached...")
r2 = req("GET", "/schedule/", token=token)
print(f"   success={r2.get('success')}, cached={r2.get('cached')}, count={r2.get('count')}")
print(f"   timings={r2.get('timings_ms')}")
if r2.get("cached") is True:
    print("   ✅ Cache HIT working!")
elif r2.get("cached") is False:
    print("   ❌ Still cache miss — MongoDB write failed")
else:
    print(f"   ⚠️  cached={r2.get('cached')}")

# 4. Summary
print("\n" + "="*50)
if r2.get("cached") is True:
    print("✅ CACHING IS WORKING CORRECTLY")
else:
    print("❌ CACHING IS STILL NOT WORKING")