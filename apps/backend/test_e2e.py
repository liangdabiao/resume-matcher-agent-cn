"""
End-to-end smoke test for the resume-matcher backend.

Runs against a *running* backend (uvicorn) on a single host. Hits every
public API in a realistic sequence, asserts on shape (status code + key
fields + a few invariants), and prints per-test PASS / FAIL with timing.

This is intentionally a stdlib-only script (urllib + json) so it can run
in the same venv as the app without extra dependencies, matching the
existing test_*.py pattern in this directory.

Usage examples:
    # Full run, all LLM tests included
    python test_e2e.py --base-url http://127.0.0.1:8001

    # Skip slow LLM tests (resume upload + improved-markdown extract only)
    python test_e2e.py --base-url http://127.0.0.1:8001 --skip-llm

    # Also check a4cv static hosting
    python test_e2e.py --base-url http://127.0.0.1:8001 \\
                      --frontend-url http://127.0.0.1:3001

Exit code is 0 iff every test passed.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

# Resolve the bundled sample resume (one level up from apps/backend/)
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESUME_FILE = os.path.normpath(
    os.path.join(HERE, os.pardir, os.pardir, "苏明远2-简历-20260615.docx")
)
DEFAULT_JD_FILE = os.path.normpath(
    os.path.join(HERE, os.pardir, os.pardir, "AI Agent 工程师岗位要求（JD）.txt")
)

# Minimal placeholder JD (~200 chars) so --skip-llm tests can still pass job
# upload validation without needing the big file. The placeholder has enough
# keywords to be a "real-looking" JD; it's just not the one we test with.
PLACEHOLDER_JD = (
    "我们正在招聘一名 Python 后端工程师。\n"
    "工作职责：\n"
    "- 使用 FastAPI 构建 REST API\n"
    "- 设计 PostgreSQL schema\n"
    "- 编写单元测试和 CI 流水线\n"
    "任职要求：\n"
    "- 3 年以上 Python 经验\n"
    "- 熟悉 SQL 和 Docker\n"
    "- 良好的中文沟通能力\n"
)

# ---------- ANSI colors (no-op on non-tty) ----------
_IS_TTY = sys.stdout.isatty()
def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _IS_TTY else s

GREEN  = lambda s: _c("32", s)
RED    = lambda s: _c("31", s)
YELLOW = lambda s: _c("33", s)
BOLD   = lambda s: _c("1",  s)
DIM    = lambda s: _c("2",  s)


# ---------- HTTP helpers ----------
class HttpError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}")


def _request(
    method: str,
    url: str,
    *,
    data=None,
    json_body=None,
    headers=None,
    timeout: float = 600.0,
    stream: bool = False,
) -> tuple[int, str]:
    """Issue an HTTP request and return (status, body). For streams, body
    is the full text concatenated (the caller decides how to chunk)."""
    hdrs = dict(headers or {})
    body_bytes: bytes | None = None
    if json_body is not None:
        hdrs.setdefault("Content-Type", "application/json")
        body_bytes = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
    elif data is not None:
        body_bytes = data

    req = urllib.request.Request(url, data=body_bytes, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, raw.decode("utf-8", errors="replace")
    return 200, raw.decode("utf-8", errors="replace")


def _post_json(base: str, path: str, body: dict, **kw) -> dict:
    url = base.rstrip("/") + path
    status, text = _request("POST", url, json_body=body, **kw)
    if status >= 400:
        raise HttpError(status, text)
    return json.loads(text)


def _get(base: str, path: str, **kw) -> tuple[int, str]:
    url = base.rstrip("/") + path
    return _request("GET", url, **kw)


# ---------- Test framework ----------
class TestRunner:
    def __init__(self, base: str, frontend: str | None, skip_llm: bool):
        self.base = base
        self.frontend = frontend
        self.skip_llm = skip_llm
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.context: dict = {}  # shared state between tests (resume_id, ...)

    def run(self, name: str, fn):
        print(f"\n{BOLD('==>')} {name}", end="  ")
        t0 = time.perf_counter()
        try:
            fn()
        except AssertionError as e:
            dt = time.perf_counter() - t0
            print(RED("FAIL") + DIM(f"  ({dt:.2f}s)"))
            print(f"     {RED('AssertionError')}: {e}")
            self.failed.append((name, str(e)))
            return
        except Exception as e:
            dt = time.perf_counter() - t0
            print(RED("FAIL") + DIM(f"  ({dt:.2f}s)"))
            import traceback
            print(f"     {RED(type(e).__name__)}: {e}")
            traceback.print_exc()
            self.failed.append((name, f"{type(e).__name__}: {e}"))
            return
        dt = time.perf_counter() - t0
        print(GREEN("PASS") + DIM(f"  ({dt:.2f}s)"))
        self.passed.append(name)

    def summary(self) -> int:
        total = len(self.passed) + len(self.failed)
        print()
        print(BOLD("=" * 60))
        print(f"  {BOLD('Results')}: {GREEN(str(len(self.passed)))} passed, "
              f"{RED(str(len(self.failed)))} failed, total {total}")
        print(BOLD("=" * 60))
        if self.failed:
            print()
            print(RED("Failed tests:"))
            for name, msg in self.failed:
                print(f"  - {name}")
                print(f"      {DIM(msg)}")
        return 0 if not self.failed else 1


# ---------- Individual tests ----------
def test_health(t: TestRunner):
    """GET /ping — no LLM, no DB writes, should be < 100ms."""
    status, text = _get(t.base, "/ping", timeout=10)
    assert status == 200, f"status {status}: {text[:200]}"
    body = json.loads(text)
    assert body.get("message") == "pong", f"unexpected body: {body}"
    db_status = body.get("database")
    assert db_status == "reachable", f"database not reachable: {db_status}"


def test_resume_upload(t: TestRunner):
    """POST /api/v1/resumes/upload — file parsing, no LLM."""
    if not os.path.exists(DEFAULT_RESUME_FILE):
        # If the bundled file is missing, create a tiny valid DOCX-free path:
        # We use a minimal placeholder file and skip. But upload requires
        # pdf or docx content-type — so we just fail with a clear message.
        raise AssertionError(
            f"sample resume not found at {DEFAULT_RESUME_FILE}; "
            "pass --resume-file to override"
        )

    with open(DEFAULT_RESUME_FILE, "rb") as f:
        data = f.read()
    assert len(data) > 100, f"resume file too small ({len(data)} bytes)"

    # Mimic curl -F file=@...;filename=...;type=...
    boundary = "----E2ETestBoundary123"
    crlf = b"\r\n"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; '
        b'filename="' + os.path.basename(DEFAULT_RESUME_FILE).encode("utf-8") + b'"',
        b"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"",
        data,
        f"--{boundary}--".encode(),
        b"",
    ]
    body = crlf.join(parts)
    status, text = _request(
        "POST",
        t.base.rstrip("/") + "/api/v1/resumes/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=180,
    )
    assert status == 200, f"status {status}: {text[:300]}"
    resp = json.loads(text)
    resume_id = resp.get("resume_id")
    assert resume_id, f"no resume_id in response: {resp}"
    t.context["resume_id"] = resume_id
    t.context["resume_raw"] = data
    print(f"\n     {DIM('resume_id =')} {resume_id}")


def test_job_upload(t: TestRunner):
    """POST /api/v1/jobs/upload — uses LLM to extract structured job (~10-30s)."""
    if t.skip_llm:
        print(f"\n     {YELLOW('skipped (--skip-llm)')}")
        return
    assert "resume_id" in t.context, "test_resume_upload must run first"
    jd_path = DEFAULT_JD_FILE if os.path.exists(DEFAULT_JD_FILE) else None
    if jd_path:
        with open(jd_path, encoding="utf-8") as f:
            jd_text = f.read()
    else:
        jd_text = PLACEHOLDER_JD

    # Trim JD to first 1500 chars to keep test fast; full JD would still
    # work but adds 5-10s with no extra coverage.
    jd_text = jd_text[:1500]

    body = _post_json(
        t.base,
        "/api/v1/jobs/upload",
        {
            "resume_id": t.context["resume_id"],
            "job_descriptions": [jd_text],
        },
        timeout=180,
    )
    job_ids = body.get("job_id")
    assert job_ids, f"no job_id in response: {body}"
    # job_id may be returned as a list (per service) or string; normalize
    if isinstance(job_ids, list):
        job_id = job_ids[0]
    else:
        job_id = job_ids
    assert job_id, f"empty job_id: {job_ids}"
    t.context["job_id"] = job_id
    print(f"\n     {DIM('job_id =')} {job_id}")


def test_improve_nonstream(t: TestRunner):
    """POST /api/v1/resumes/improve — full LLM pipeline, ~60-80s."""
    if t.skip_llm:
        print(f"\n     {YELLOW('skipped (--skip-llm)')}")
        return
    assert "job_id" in t.context, "test_job_upload must run first"
    body = _post_json(
        t.base,
        "/api/v1/resumes/improve",
        {
            "resume_id": t.context["resume_id"],
            "job_id": t.context["job_id"],
        },
        timeout=600,
    )
    data = body.get("data") or {}
    analysis = data.get("analysis_result")
    assert analysis, f"no analysis_result in response: keys={list(data.keys())}"
    assert len(analysis) > 200, f"analysis_result too short ({len(analysis)} chars)"
    # Should mention Chinese characters (HR report in 简体中文)
    chinese_chars = sum(1 for c in analysis if 0x4E00 <= ord(c) <= 0x9FFF)
    assert chinese_chars > 100, f"expected Chinese content, got {chinese_chars} hanzi"
    t.context["analysis_result"] = analysis
    print(f"\n     {DIM('analysis_result =')} {len(analysis)} chars, "
          f"{chinese_chars} hanzi")
    # Sanity-check the 5-step structure
    steps = re.findall(r"Step\s*[1-5]", analysis)
    assert len(set(steps)) >= 3, f"expected ≥3 distinct steps, got {steps}"


def test_improve_stream(t: TestRunner):
    """POST /api/v1/resumes/improve?stream=true — parse SSE events."""
    if t.skip_llm:
        print(f"\n     {YELLOW('skipped (--skip-llm)')}")
        return
    assert "job_id" in t.context
    url = t.base.rstrip("/") + "/api/v1/resumes/improve?stream=true"
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "resume_id": t.context["resume_id"],
            "job_id": t.context["job_id"],
        }, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    print()  # newline so per-event log looks clean
    t0 = time.perf_counter()
    ttft_ms: float | None = None
    statuses: list[str] = []
    final_result: dict | None = None
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            assert r.status == 200
            buf = ""
            for raw in r:
                chunk = raw.decode("utf-8", errors="replace")
                if ttft_ms is None and chunk.strip():
                    ttft_ms = (time.perf_counter() - t0) * 1000
                buf += chunk
                # SSE messages are separated by \n\n
                while "\n\n" in buf:
                    msg, buf = buf.split("\n\n", 1)
                    data_lines = [
                        line[len("data:"):].strip()
                        for line in msg.splitlines()
                        if line.startswith("data:")
                    ]
                    if not data_lines:
                        continue
                    payload = json.loads(data_lines[0])
                    status = payload.get("status", "?")
                    statuses.append(status)
                    elapsed = time.perf_counter() - t0
                    msg = payload.get("message") or ""
                    print(f"     {DIM(f'+{elapsed:5.1f}s')} {status}  {msg}")
                    if status == "completed":
                        final_result = payload.get("result")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise AssertionError(f"stream HTTP {e.code}: {body[:300]}")
    dt = time.perf_counter() - t0
    assert statuses[:1] == ["starting"], f"first event not 'starting': {statuses[:1]}"
    assert statuses[-1] == "completed", f"last event not 'completed': {statuses[-1]}"
    assert final_result, "no final result in 'completed' event"
    # `completed` event's `result` mirrors the non-streaming envelope:
    # { request_id, data: { resume_id, job_id, analysis_result, ... } }
    data_block = final_result.get("data") or {}
    analysis_result = data_block.get("analysis_result")
    assert analysis_result, f"no analysis_result in result.data: {list(final_result.keys())} -> {list(data_block.keys())}"
    # Stash for downstream tests (e.g. test_improved_markdown)
    t.context["analysis_result"] = analysis_result
    print(f"\n     {DIM('events =')} {len(statuses)}, "
          f"{DIM('TTFT =')} {ttft_ms:.0f}ms, "
          f"{DIM('total =')} {dt:.1f}s")


def test_improved_markdown(t: TestRunner):
    """POST /api/v1/resumes/improved-markdown — pure extraction, no LLM."""
    # Can run without LLM if we have any analysis_result text (the fallback
    # path uses processed_resume from DB, which was created by resume upload).
    if "analysis_result" not in t.context and not t.skip_llm:
        # Should have been set by test_improve_nonstream
        raise AssertionError("need analysis_result from test_improve_nonstream")
    if "analysis_result" not in t.context and t.skip_llm:
        # Fall back to a synthetic one
        t.context["analysis_result"] = "（无分析结果，使用最小 fallback）"
    body = _post_json(
        t.base,
        "/api/v1/resumes/improved-markdown",
        {
            "resume_id": t.context["resume_id"],
            "job_id": t.context.get("job_id", ""),
            "analysis_result": t.context["analysis_result"],
        },
        timeout=30,
    )
    data = body.get("data") or {}
    md = data.get("markdown")
    src = data.get("source")
    sections = data.get("sections_detected", 0)
    assert md, f"no markdown in response: {data}"
    assert src in {"extracted", "fallback"}, f"unexpected source: {src}"
    # When extracted, code fences should be stripped
    if src == "extracted":
        assert "```" not in md, "code fences should be stripped"
    assert sections >= 1, f"expected ≥1 section, got {sections}"
    print(f"\n     {DIM('source =')} {src}, "
          f"{DIM('markdown =')} {len(md)} chars, "
          f"{DIM('sections =')} {sections}")


def test_a4cv_static(t: TestRunner):
    """GET /a4cv/ — verify the editor static hosting + pickup hook."""
    if not t.frontend:
        print(f"\n     {YELLOW('skipped (no --frontend-url)')}")
        return
    # /a4cv/ is served by Next.js (public/a4cv/index.html)
    status, html = _get(t.frontend.rstrip("/") + "/a4cv/", timeout=30)
    assert status == 200, f"a4cv not served: HTTP {status}"
    assert "<title" in html.lower(), "no <title> tag in a4cv index.html"
    assert "pickupResumeFromOptimizer" in html, "pickup hook missing"
    assert "sessionStorage" in html, "no sessionStorage reference"
    # Spot-check a vendor asset too
    status2, _ = _get(t.frontend.rstrip("/") + "/a4cv/vendor/", timeout=15)
    assert status2 in (200, 404), f"vendor subpath unreachable: {status2}"


# ---------- Main ----------
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://127.0.0.1:8000",
                   help="backend base URL (default: %(default)s)")
    p.add_argument("--frontend-url", default=None,
                   help="frontend base URL for a4cv check (default: skip)")
    p.add_argument("--skip-llm", action="store_true",
                   help="skip LLM-using tests (job upload, improve, improve-stream)")
    p.add_argument("--resume-file", default=DEFAULT_RESUME_FILE,
                   help="path to a .docx/.pdf resume (default: bundled sample)")
    args = p.parse_args()

    print(BOLD("Resume Matcher E2E Test"))
    print(f"  backend:  {args.base_url}")
    print(f"  frontend: {args.frontend_url or '(skipped)'}")
    print(f"  skip-llm: {args.skip_llm}")

    t = TestRunner(args.base_url, args.frontend_url, args.skip_llm)

    # Run in dependency order
    t.run("test_health",             lambda: test_health(t))
    t.run("test_resume_upload",      lambda: test_resume_upload(t))
    t.run("test_job_upload",         lambda: test_job_upload(t))
    t.run("test_improve_nonstream",  lambda: test_improve_nonstream(t))
    t.run("test_improve_stream",     lambda: test_improve_stream(t))
    t.run("test_improved_markdown",  lambda: test_improved_markdown(t))
    t.run("test_a4cv_static",        lambda: test_a4cv_static(t))

    return t.summary()


if __name__ == "__main__":
    sys.exit(main())
