"""Verify a4cv vendor scripts are served by Next.js."""
import sys
import urllib.request
import urllib.error

VENDOR_FILES = [
    "vendor/marked.min.js",
    "vendor/mammoth.browser.min.js",
    "vendor/Sortable.min.js",
    "vendor/html2canvas.min.js",
    "vendor/jspdf.umd.min.js",
]

ok = 0
for f in VENDOR_FILES:
    url = f"http://localhost:3001/a4cv/{f}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            length = len(r.read())
            print(f"OK  {r.status}  {f}  (len={length})")
            ok += 1
    except urllib.error.HTTPError as e:
        print(f"{e.code}  {f}")

print(f"\n{ok}/{len(VENDOR_FILES)} vendor files served")
sys.exit(0 if ok == len(VENDOR_FILES) else 1)
