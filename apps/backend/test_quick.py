"""Quick connectivity check - much smaller version."""
import sys
import urllib.request
import traceback

try:
    with urllib.request.urlopen("http://localhost:3001/a4cv/", timeout=30) as r:
        print("status:", r.status)
        html = r.read().decode("utf-8", errors="replace")
        print("length:", len(html))
        print("---first 800 chars---")
        print(html[:800])
except Exception as e:
    print("EXC:", type(e).__name__, e)
    traceback.print_exc()
    sys.exit(1)
