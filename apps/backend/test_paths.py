"""Test with explicit index.html path."""
import sys
import urllib.request
import urllib.error
import traceback

URLS = [
    "http://localhost:3001/a4cv",
    "http://localhost:3001/a4cv/",
    "http://localhost:3001/a4cv/index.html",
    "http://localhost:3001/dashboard",
]

for url in URLS:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            html = r.read()
            print(f"OK  {r.status}  {url}  (len={len(html)})")
    except urllib.error.HTTPError as e:
        body = e.read()[:200]
        print(f"{e.code}  {url}  body={body!r}")
    except Exception as e:
        print(f"EXC {url}: {type(e).__name__} {e}")
