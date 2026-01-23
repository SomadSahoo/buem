#!/usr/bin/env python3
"""
Simple CLI to POST a GeoJSON file to the BUEM API (acts like curl).
Usage:
  python src/buem/integration/send_geojson.py request_template.geojson \
    --url http://127.0.0.1:5000/api/process --include-timeseries
"""
import argparse
import json
import sys
import requests
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description="Send GeoJSON to BUEM API")
    p.add_argument("file", type=Path, help="Path to GeoJSON file")
    p.add_argument("--url", default="http://127.0.0.1:5000/api/process", help="Endpoint URL")
    p.add_argument("--include-timeseries", action="store_true", help="Request full timeseries in response")
    p.add_argument("--timeout", type=int, default=120, help="Request timeout seconds")
    args = p.parse_args()

    if not args.file.exists():
        print("Error: file not found:", args.file, file=sys.stderr)
        sys.exit(2)

    with args.file.open("r", encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except Exception as e:
            print("Invalid JSON file:", e, file=sys.stderr)
            sys.exit(3)

    params = {}
    if args.include_timeseries:
        params["include_timeseries"] = "true"

    try:
        r = requests.post(args.url, json=payload, params=params, timeout=args.timeout)
    except Exception as e:
        print("Request failed:", e, file=sys.stderr)
        sys.exit(4)

    print("HTTP", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

if __name__ == "__main__":
    main()