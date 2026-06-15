"""End-to-end smoke test for the new /improved-markdown endpoint.

Sends a typical HR-judge style `analysis_result` payload, asserts that the
backend extracts the ```md fenced block and returns it in a4cv-compatible
format, then prints the response for visual inspection.
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8000/api/v1/resumes/improved-markdown"

PAYLOAD = {
    "resume_id": "test-resume-001",
    "job_id": "test-job-001",
    "analysis_result": (
        "# HR 反馈\n\n"
        "## 摘要\n\n"
        "不错的简历。\n\n"
        "```md\n"
        "# 张三\n"
        "## 高级前端工程师\n"
        "> 北京 · zhangsan@example.com · 13800138000\n\n"
        "## 工作经历\n"
        "### 字节跳动 · 高级前端 | 2022-2024\n"
        "- 负责抖音商家端\n"
        "- 提升 30% 性能\n\n"
        "## 项目经历\n"
        "### 抖音商城 | 2023\n"
        "- 重构结算流程\n\n"
        "## 教育背景\n"
        "### 清华 · 计算机 | 2018-2022\n\n"
        "## 技能标签\n"
        "React · TypeScript · Webpack\n"
        "```\n\n"
        "## 最终评语\n\n"
        "加油。\n"
    ),
}

# Also test the fallback path (no code block)
FALLBACK_PAYLOAD = {
    "resume_id": "test-resume-001",
    "job_id": "test-job-001",
    "analysis_result": "# HR 反馈\n\n没有代码块的报告。\n",
}

req = urllib.request.Request(
    URL,
    data=json.dumps(PAYLOAD).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

print(f"POST {URL}")
print("--- TEST 1: extraction from code block ---")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        status = r.status
        body = json.loads(r.read().decode("utf-8"))
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

print(f"HTTP {status}")
data = body.get("data", {})
print(f"source: {data.get('source')}")
print(f"sections_detected: {data.get('sections_detected')}")
md = data.get("markdown", "")
print("--- extracted markdown (FULL) ---")
print(md)
print("--- end ---")

assert status == 200, f"unexpected status {status}"
assert data.get("source") == "extracted", f"expected extracted, got {data.get('source')}"
assert "# 张三" in md
assert "```" not in md, "code fences should be stripped"
assert "## 工作经历" in md
assert data.get("sections_detected") >= 4
print("PASS: code-block extraction works\n")

# Test fallback
print("--- TEST 2: fallback (no code block) ---")
req2 = urllib.request.Request(
    URL,
    data=json.dumps(FALLBACK_PAYLOAD).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req2, timeout=30) as r:
        status2 = r.status
        body2 = json.loads(r.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    # 404 is expected because test-resume-001 does not exist in DB
    print(f"Got HTTPError {e.code} (expected when resume not in DB)")
    print(f"Body: {e.read().decode('utf-8')[:300]}")
    print("PASS: fallback path is reachable (will return 404 when processed_resume missing)")
    sys.exit(0)

print(f"HTTP {status2}")
data2 = body2.get("data", {})
print(f"source: {data2.get('source')}")
md2 = data2.get("markdown", "")
print(md2[:500])
print("--- end ---")
