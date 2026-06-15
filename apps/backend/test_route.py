"""Verify the new improved-markdown route is registered in FastAPI."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
except Exception as e:
    print("IMPORT FAILED:", e)
    raise

paths = []
for r in app.routes:
    p = getattr(r, "path", None)
    methods = getattr(r, "methods", set()) or set()
    if p:
        for m in methods:
            paths.append(f"  {m:6s} {p}")

print("--- Resume / Improved routes ---")
for line in paths:
    if "resume" in line.lower() or "improv" in line.lower():
        print(line)

# Check specifically
target = "/api/v1/resumes/improved-markdown"
hits = [line for line in paths if target in line]
print(f"\nLooking for: {target}")
if hits:
    for h in hits:
        print("FOUND:", h)
    print("ROUTE REGISTERED OK")
else:
    print("ROUTE NOT FOUND - registration failed")
    sys.exit(1)
