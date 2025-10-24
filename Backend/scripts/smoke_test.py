"""Simple smoke test for backend endpoints.

Runs a short set of GET requests against common endpoints and prints
status codes and a small preview of JSON or text returned.
"""
import json
# minimal smoke-test; avoid unused imports

import requests


ENDPOINTS = [
    "/health",
    "/models",
    "/gpu-status",
    "/songs",
]


def fetch(base_url="http://127.0.0.1:5000"):
    results = []
    for ep in ENDPOINTS:
        url = base_url.rstrip("/") + ep
        try:
            r = requests.get(url, timeout=5)
            entry = {"endpoint": ep, "status_code": r.status_code}
            try:
                entry["json"] = r.json()
            except Exception:
                entry["text"] = r.text[:1000]
        except Exception as e:  # network error / timeout
            entry = {"endpoint": ep, "error": str(e)}
        results.append(entry)
    return results


def main():
    print("Running backend smoke tests against http://127.0.0.1:5000")
    res = fetch()
    for r in res:
        ep = r.get("endpoint")
        if "error" in r:
            print(f"{ep}: ERROR -> {r['error']}")
            continue
        print(f"{ep}: {r.get('status_code')}")
        if "json" in r:
            try:
                pretty = json.dumps(r["json"], indent=2)
                print(pretty[:4000])
            except Exception:
                print("<non-serializable json>")
        elif "text" in r:
            print(r["text"])
        print("-" * 60)


if __name__ == "__main__":
    main()
