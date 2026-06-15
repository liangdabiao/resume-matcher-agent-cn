"""Profile a single /improve call to find the bottleneck."""
import time, json, requests, sys

# 1) Health
t0 = time.perf_counter()
r = requests.get("http://127.0.0.1:8000/api/v1/ping", timeout=5)
print(f"[ping] {r.status_code}  {(time.perf_counter()-t0)*1000:.0f}ms")

# 2) Find a known resume_id+job_id from the test data, or upload fresh
# The user provided these IDs:
resume_id = "e1142590-71a8-4cdd-b8d9-fb0cb1a34cdc"
job_id    = "30178682-9061-455c-8039-ef3ef4c32fd5"

# 3) Hit /improve WITHOUT stream and time the full RTT
print("\n[/improve non-stream] start...")
t1 = time.perf_counter()
r = requests.post(
    "http://127.0.0.1:8000/api/v1/resumes/improve",
    json={"resume_id": resume_id, "job_id": job_id},
    timeout=600,
)
elapsed = time.perf_counter() - t1
data = r.json().get("data", {}) or {}
ar = data.get("analysis_result") or ""
print(f"  HTTP {r.status_code}  total RTT = {elapsed:.2f}s  result_len = {len(ar)} chars")

# 4) Hit /improve WITH stream and measure TTFT + total
print("\n[/improve stream] start...")
t2 = time.perf_counter()
ttft = None
total_bytes = 0
last_status = None
with requests.post(
    "http://127.0.0.1:8000/api/v1/resumes/improve?stream=true",
    json={"resume_id": resume_id, "job_id": job_id},
    stream=True,
    timeout=600,
) as r:
    for chunk in r.iter_content(chunk_size=1):
        total_bytes += len(chunk)
        if ttft is None and chunk:
            ttft = time.perf_counter() - t2
stream_elapsed = time.perf_counter() - t2
print(f"  TTFT = {ttft*1000:.0f}ms" if ttft else "  TTFT = N/A")
print(f"  total stream RTT = {stream_elapsed:.2f}s  bytes = {total_bytes}")
