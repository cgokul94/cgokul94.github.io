#!/usr/bin/env python3
"""Fetch citation stats from OpenAlex and write data/citations.json.

Resolution order for the author:
  1. OPENALEX_AUTHOR_ID env var, if set (e.g. "A5012345678") — exact, no search needed.
  2. Name search for "Gokul Chandrasekaran", preferring a result affiliated with
     Arizona State University.

Writes {"citations": int, "works": int, "h_index": int, "updated": "YYYY-MM-DD",
"author_id": str, "author_name": str} to data/citations.json. Exits 0 without
writing on any lookup/network failure so a bad day on the API never breaks the
site or fails the workflow loudly.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import date

API_BASE = "https://api.openalex.org"
MAILTO = "gchandr8@asu.edu"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "citations.json")


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"cgokul94.github.io citation widget (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def resolve_author():
    pinned_id = os.environ.get("OPENALEX_AUTHOR_ID", "").strip()
    if pinned_id:
        data = fetch_json(f"{API_BASE}/authors/{pinned_id}?mailto={MAILTO}")
        return data

    query = urllib.parse.urlencode({"search": "Gokul Chandrasekaran", "mailto": MAILTO})
    results = fetch_json(f"{API_BASE}/authors?{query}").get("results", [])
    if not results:
        raise RuntimeError("no OpenAlex author results for 'Gokul Chandrasekaran'")

    for candidate in results:
        institutions = candidate.get("last_known_institutions") or []
        if any("arizona state" in (inst.get("display_name") or "").lower() for inst in institutions):
            return candidate

    print("warning: no candidate matched Arizona State University; using first result", file=sys.stderr)
    return results[0]


def main():
    try:
        author = resolve_author()
    except Exception as exc:
        print(f"skipping update: {exc}", file=sys.stderr)
        return 0

    payload = {
        "citations": author.get("cited_by_count"),
        "works": author.get("works_count"),
        "h_index": (author.get("summary_stats") or {}).get("h_index"),
        "author_id": author.get("id"),
        "author_name": author.get("display_name"),
        "updated": date.today().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"wrote {OUTPUT_PATH}: {payload}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
