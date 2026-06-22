"""
Performance measurement script for UIT TKB Scraper API.

Runs requests against a running instance of the API and collects
timing data from response headers and body.

Usage:
    # First, start the server:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    
    # Then run this script:
    python scripts/measure_performance.py [--base-url http://localhost:8000]
"""

import time
import sys
import json
import argparse
from datetime import datetime

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)


def timing_header(name: str, value: str) -> str:
    return f"  {name:40s} {value:>10s}"


def measure_endpoint(client: httpx.Client, method: str, url: str,
                     headers: dict = None, label: str = None,
                     use_cache: bool = False) -> dict:
    """Measure a single request and extract timing data."""
    req_headers = headers or {}
    
    start = time.perf_counter()
    
    if method.upper() == "GET":
        resp = client.get(url, headers=req_headers)
    elif method.upper() == "POST":
        resp = client.post(url, headers=req_headers)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    wall_clock_ms = (time.perf_counter() - start) * 1000.0
    
    # Extract response body
    try:
        body = resp.json()
    except Exception:
        body = {}
    
    # Extract timings from response headers
    header_timings = {}
    for key, value in resp.headers.items():
        if key.startswith("X-Timing-"):
            name = key.replace("X-Timing-", "").replace("_", " ").strip()
            header_timings[name] = value
    
    # Extract timings from body
    body_timings = body.get("timings_ms", {})
    cached = body.get("cached", False)
    
    result = {
        "endpoint": label or url,
        "method": method,
        "url": url,
        "status_code": resp.status_code,
        "cached": cached,
        "wall_clock_ms": round(wall_clock_ms, 1),
        "header_timings": header_timings,
        "body_timings": body_timings,
        "response_size_bytes": len(resp.content),
        "response_time_header": resp.headers.get("X-Timing-Total-Ms", "N/A"),
    }
    
    return result


def print_result(result: dict):
    """Print a formatted timing result."""
    print(f"\n{'='*70}")
    print(f"  Endpoint: {result['endpoint']}")
    print(f"  Method:   {result['method']}")
    print(f"  URL:      {result['url']}")
    print(f"  Status:   {result['status_code']}")
    print(f"  Cached:   {result['cached']}")
    print(f"  Size:     {result['response_size_bytes']:,} bytes")
    print(f"{'─'*70}")
    print(f"  {'Phase':40s} {'Time (ms)':>10s}")
    print(f"{'─'*70}")
    
    # Header timings from middleware
    if result["header_timings"]:
        for name, ms in sorted(result["header_timings"].items()):
            print(f"  {name:40s} {ms:>10s}")
    
    # Body timings from route handlers
    if result["body_timings"]:
        print(f"  {'[Route timings]':40s}")
        for name, ms in sorted(result["body_timings"].items()):
            print(f"  {name:40s} {ms:>8.1f} ms")
    
    print(f"{'─'*70}")
    print(f"  {'Wall clock (measured)':40s} {result['wall_clock_ms']:>10.1f} ms")
    print(f"  {'Response header X-Timing-Total':40s} {result['response_time_header']:>10s}")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(description="Measure API request lifecycle timing")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--token", default=None,
                        help="Auth token for authenticated endpoints")
    args = parser.parse_args()
    
    base = args.base_url.rstrip("/")
    
    with httpx.Client(base_url=base, timeout=60.0) as client:
        print(f"\n{'#'*70}")
        print(f"  UIT TKB Scraper - Performance Measurement")
        print(f"  Target: {base}")
        print(f"  Time:   {datetime.now().isoformat()}")
        print(f"{'#'*70}")
        
        # === 1. Health check / cold start ===
        print(f"\n{'#'*70}")
        print(f"  PHASE 1: Cold Start Measurement")
        print(f"{'#'*70}")
        
        # First request (cold start)
        result = measure_endpoint(client, "GET", "/", label="GET / (cold start)")
        print_result(result)
        
        # Warm request
        result = measure_endpoint(client, "GET", "/", label="GET / (warm)")
        print_result(result)
        
        # Timing stats
        result = measure_endpoint(client, "GET", "/timing-stats", label="GET /timing-stats")
        print_result(result)
        
        # === 2. MongoDB query endpoints ===
        print(f"\n{'#'*70}")
        print(f"  PHASE 2: MongoDB Query Performance")
        print(f"{'#'*70}")
        
        result = measure_endpoint(client, "GET", "/announcements/?limit=5",
                                  label="GET /announcements/ (MongoDB query)")
        print_result(result)
        
        result = measure_endpoint(client, "GET", "/announcements/?limit=5",
                                  label="GET /announcements/ (MongoDB cached)")
        print_result(result)
        
        # === 3. Auth endpoints ===
        print(f"\n{'#'*70}")
        print(f"  PHASE 3: Auth Endpoint Performance")
        print(f"{'#'*70}")
        
        # Note: login won't work without valid credentials, but we measure the attempt
        result = measure_endpoint(client, "POST", "/auth/login",
                                  headers={"Content-Type": "application/json"},
                                  label="POST /auth/login (no body - error path)")
        print_result(result)
        
        # Logout without token
        result = measure_endpoint(client, "POST", "/auth/logout",
                                  label="POST /auth/logout")
        print_result(result)
        
        # === 4. Authenticated endpoints (if token provided) ===
        if args.token:
            auth_headers = {"Authorization": f"Bearer {args.token}"}
            
            print(f"\n{'#'*70}")
            print(f"  PHASE 4: Authenticated Endpoint Performance (CACHE MISS)")
            print(f"{'#'*70}")
            
            # Schedule (cache miss - scrapes from UIT)
            result = measure_endpoint(client, "GET", "/schedule/?refresh=true",
                                      headers=auth_headers,
                                      label="GET /schedule/ (cache miss - scrape)")
            print_result(result)
            
            # Schedule (cache hit)
            result = measure_endpoint(client, "GET", "/schedule/",
                                      headers=auth_headers,
                                      label="GET /schedule/ (cache hit)")
            print_result(result)
            
            # Exam schedule
            result = measure_endpoint(client, "GET", "/schedule/exam?lanthi=1&hocky=1&namhoc=2024",
                                      headers=auth_headers,
                                      label="GET /schedule/exam (cache miss)")
            print_result(result)
            
            # Grades
            result = measure_endpoint(client, "GET", "/grades/",
                                      headers=auth_headers,
                                      label="GET /grades/ (cache miss - scrape)")
            print_result(result)
            
            result = measure_endpoint(client, "GET", "/grades/",
                                      headers=auth_headers,
                                      label="GET /grades/ (cache hit)")
            print_result(result)
            
            # Tuition
            result = measure_endpoint(client, "GET", "/tuition/",
                                      headers=auth_headers,
                                      label="GET /tuition/ (cache miss - scrape)")
            print_result(result)
            
            result = measure_endpoint(client, "GET", "/tuition/summary",
                                      headers=auth_headers,
                                      label="GET /tuition/summary")
            print_result(result)
            
            # Deadlines
            result = measure_endpoint(client, "GET", "/deadlines/?refresh=true",
                                      headers=auth_headers,
                                      label="GET /deadlines/ (Moodle scrape)")
            print_result(result)
            
        else:
            print(f"\n  ⚠ No auth token provided. Skipping authenticated endpoints.")
            print(f"  Provide --token <token> to measure authenticated routes.")
        
        # === Summary ===
        print(f"\n{'#'*70}")
        print(f"  SUMMARY")
        print(f"{'#'*70}")
        print(f"  See individual measurements above.")
        print(f"  Key metrics to look for:")
        print(f"  - Cold start time (first request)")
        print(f"  - MongoDB query time vs total response time")
        print(f"  - Scrape time for UIT/Moodle endpoints")
        print(f"  - Cache hit vs cache miss comparison")
        print(f"{'#'*70}\n")


if __name__ == "__main__":
    main()